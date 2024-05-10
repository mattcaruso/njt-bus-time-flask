import os
import psycopg2
import pytz
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, Response, jsonify, request
from psycopg2 import extras

app = Flask(__name__)
executor = ThreadPoolExecutor(2)

# As a workaround to the deprecation of @app.before_first_request, we'll use this flag to utilize the built-in
# @app.before_request method which runs on every request. Only the first time, we'll flip this to True to bypass
# the before_request function every other time.\
# NOTE: This will run once per Gunicorn worker. The state of variables isn't shared across workers.
initialized = False

# app.register_blueprint(errors)
# TODO Exit container if the /data volume doesn't exist


def open_connection():
    return psycopg2.connect(
        host=os.environ['PGHOST'],
        port=os.environ['PGPORT'],
        database=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD']
    )


def api_key_required(func):
    def decorator(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        print("KEY FROM HEADERS:", api_key)
        print("KEY FROM ENVIRON:", os.environ['API_KEY'])
        if api_key == os.environ['API_KEY']:
            return func(*args, **kwargs)
        else:
            return {"message": "Please provide a valid API key"}, 400
    return decorator


@app.before_request
def before_request():
    global initialized
    query = f"""
    DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'imports') THEN
                CREATE TABLE imports (
                    id SERIAL PRIMARY KEY,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    url VARCHAR(255),
                    success BOOLEAN DEFAULT TRUE
                );
            END IF;
        END $$;
    """
    if not initialized:
        conn = open_connection()
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        initialized = True
        print('Ensured existence of imports table.')


@app.route("/stops/<stop_code>/<route_name>/next_departures", methods=["GET"])
def next_departures_api(stop_code, route_name):
    departures_string = next_departures(stop_code, route_name)
    return jsonify(departures_string)


def next_departures(stop_code: str, route_name: str) -> str:
    conn = open_connection()
    cur = conn.cursor(cursor_factory=extras.DictCursor)

    # Timezone can be hardcoded throughout the app because NJ Transit only exists in Eastern time.
    now = datetime.now(pytz.timezone('America/New_York'))
    weekday = now.weekday()

    if weekday == 5:  # Saturday
        service_id = 1
    elif weekday == 6:  # Sunday
        service_id = 2
    else:  # Weekdays
        service_id = 3

    query = f"""
            with stx as (
            select
                *,
                CASE
                    WHEN substring(arrival_time from 1 for 2)::int > 23 THEN
                        CASE
                            WHEN length(substring(arrival_time from 1 for 2)::text) = 1 THEN
                                '0' || (substring(arrival_time from 1 for 2)::int - 24)::text || substring(arrival_time from 3)
                            ELSE
                                (substring(arrival_time from 1 for 2)::int - 24)::text || substring(arrival_time from 3)
                        END
                    ELSE
                        arrival_time
                END as arrival_time_cleaned
            from stop_times
        ),
        -- We can use this internal pg_catalog table to use a static reference to the time zone,
        -- which will allow us to reference the utc offset value through both Standard Time & DST months.
        nyctz as (
            select * from pg_catalog.pg_timezone_names
            where name = 'America/New_York'
        )


        select
            stx.stop_id,
            s.stop_code,
            stx.trip_id,
            r.route_short_name,
            t.service_id,
            stx.arrival_time as arrival_time_text,
            stx.arrival_time_cleaned,
            cast(stx.arrival_time_cleaned || nyctz.utc_offset as timetz) as local_time,
            CURRENT_TIME AT TIME ZONE 'America/New_York' as current_time
        from stx
        join stops s on s.stop_id = stx.stop_id
        join trips t on t.trip_id = stx.trip_id
        join routes r on r.route_id = t.route_id
        join nyctz on 1=1


        where cast(stx.arrival_time_cleaned || nyctz.utc_offset as timetz) > CURRENT_TIME AT TIME ZONE 'America/New_York'
        and s.stop_code = '{stop_code}'
        AND t.service_id in ('{service_id}')  -- 1 Saturday, 2 Sunday, 3 Weekdays
        and r.route_short_name = '{route_name}'

        order by stx.stop_id, stx.arrival_time_cleaned
        limit 2
    """
    cur.execute(query)
    stops = cur.fetchall()
    cur.close()
    conn.close()

    response = []

    for stop in stops:
        local_time = stop['local_time']
        pretty_time = local_time.strftime('%-I:%M%p')
        response.append(pretty_time)

    return '  '.join(response)


@app.route("/health")
def health():
    return Response("OK", status=200)


def render_pixlet() -> str:
    """Returns the rendered image for Tidbyt as a base64-encoded string"""

    # TODO Refactor with Stop Code in config
    bus1_next_times = next_departures('21055', '123')
    bus2_next_times = next_departures('21073', '84')
    print('123 NEXT TIMES:', bus1_next_times)
    print('84 NEXT TIMES:', bus2_next_times)

    url = 'https://pixlet.palisadezoo.com'
    params = {
        'output': 'base64',  # Tidbyt API requires images to be base64
        'applet': 'https://raw.githubusercontent.com/mattcaruso/njt-bus-time-flask/main/api/njt_bus.star',
        'bus1_line': '123',
        'bus1_headsign': 'NEW YORK',
        'bus1_next_times': bus1_next_times,
        'bus2_line': '84',
        'bus2_headsign': 'JOURNAL SQ',
        'bus2_next_times': bus2_next_times
    }

    response = requests.get(url, params=params)
    print('Response from Axilla Pixlet:', response.status_code)
    return response.text


def push_to_tidbyt(device_id: str, api_key: str, image_base64: str) -> requests.Response:
    """
    Sends the image to Tidbyt
    https://tidbyt.dev/docs/api
    """
    print(f'Pushing to device {device_id}')

    base_url = 'https://api.tidbyt.com'
    push_url = f'{base_url}/v0/devices/{device_id}/push'

    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    body = {
        'image': image_base64,
        'installationID': 'njtbustimes',
        'background': True
    }

    response = requests.post(url=push_url, headers=headers, json=body)
    print(f'Response from Tidbyt: {response.status_code}: {response.text}')

    return response


@app.route('/push', methods=['GET'])
def push():
    print('Push to Tidbyt requested')

    image_base64 = render_pixlet()

    device_ids = os.environ['TIDBYT_DEVICE_IDS'].split(',')
    api_keys = os.environ['TIDBYT_API_KEYS'].split(',')

    for i, device_id in enumerate(device_ids):
        api_key = api_keys[i]
        push_to_tidbyt(device_id, api_key, image_base64)

    return jsonify('Request to push sent to Tidbyt')


@app.route('/load', methods=['GET'])
def request_load_gtfs():
    args = request.args
    gtfs_url = args.get('gtfs')

    if not gtfs_url:
        # Will be NoneType if not found
        return Response('Missing required parameter', status=400)

    executor.submit(load_gtfs, gtfs_url)

    return Response('Requested GTFS import', status=202)


@app.route('/imports', methods=['GET'])
@api_key_required
def get_imports():

    query = f"""
        SELECT * FROM imports ORDER BY time DESC LIMIT 5
    """
    conn = open_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(query)
    imports = cur.fetchall()

    # Add a derived key which converts the time to eastern time
    [i.update({'time_et': convert_to_nj_time(i['time'])}) for i in imports]

    cur.close()
    conn.close()

    return jsonify(imports)


def convert_to_nj_time(utc_time: datetime):
    # Make the UTC time aware of its timezone
    utc_time = pytz.timezone('UTC').localize(utc_time)

    # Convert to Eastern time; will be aware of daylight savings
    new_york_time = utc_time.astimezone(pytz.timezone('America/New_York'))
    formatted_time = new_york_time.strftime('%Y-%m-%d %I:%M%p')

    return formatted_time


def load_gtfs(gtfs_url):
    print('*** BEGIN GTFS LOAD')
    gtfsdb_to_sqlite(gtfs_url)
    ingest_sqlite_to_postgres(
        f'postgresql://{os.environ["PGUSER"]}:'
        f'{os.environ["PGPASSWORD"]}@{os.environ["PGHOST"]}:'
        f'{os.environ["PGPORT"]}/{os.environ["PGDATABSE"]}'
    )
    record_import(gtfs_url)
    print('*** GTFS LOAD COMPLETED')


def gtfsdb_to_sqlite(gtfs_url):
    """Uses the gtfsdb source code to run a CLI to generate a sqlite db from a GTFS file."""
    subprocess.call([
        '/app/bin/gtfsdb/bin/gtfsdb-load',
        '--tables',
        'stops',
        'agency',
        'calendar_dates',
        'route_directions',
        'route_filters',
        'route_type',
        'routes',
        'stop_times',
        'trips',
        'universal_calendar',
        '--ignore_postprocess',
        '--database_url',
        'sqlite:////data/gtfs.sqlite3',
        gtfs_url
    ])


def ingest_sqlite_to_postgres(postgres_url):
    subprocess.call([
        'pgloader',
        'sqlite:////data/gtfs.sqlite3',
        postgres_url
    ])


def record_import(url: str):

    query = f"INSERT INTO imports (url) VALUES ('{url}');"
    conn = open_connection()
    cur = conn.cursor()
    cur.execute(query)
    conn.commit()
    cur.close()
    conn.close()
