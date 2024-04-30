import os
import psycopg2
import pytz
import requests

from datetime import datetime
from flask import Flask, Response, jsonify
from flask_apscheduler import APScheduler
from psycopg2 import extras

from .errors import errors

app = Flask(__name__)
app.register_blueprint(errors)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# TODO Add authentication (Is this necessary if it's only outgoing traffic?)

conn = psycopg2.connect(
    host=os.environ['PGHOST'],
    port=os.environ['PGPORT'],
    database=os.environ['PGDATABASE'],
    user=os.environ['PGUSER'],
    password=os.environ['PGPASSWORD']
)


@app.route("/stops/<stop_code>/<route_name>/next_departures", methods=["GET"])
def next_departures_api(stop_code, route_name):
    departures_string = next_departures(stop_code, route_name)
    return jsonify(departures_string)


def next_departures(stop_code: str, route_name: str) -> str:
    # Open a cursor to perform database operations
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

    url = 'https://pixlet.palisadezoo.com'
    params = {
        'output': 'base64',  # Tidbyt API requires images to be base64
        'applet': 'https://raw.githubusercontent.com/mattcaruso/njt-bus-time-flask/main/api/njt_bus.star',
        'bus1_line': '123',
        'bus1_headsign': 'NEW YORK',
        'bus1_next_times': next_departures('21055', '123'),  # TODO Refactor with Stop Code in config
        'bus2_line': '84',
        'bus2_headsign': 'JOURNAL SQ',
        'bus2_next_times': next_departures('21073', '84')
    }

    response = requests.get(url, params=params)
    return response.text


def push_to_tidbyt(device_ids: list) -> requests.Response:
    """
    Sends the image to Tidbyt
    https://tidbyt.dev/docs/api
    """
    if not isinstance(device_ids, list):
        raise TypeError('device_ids must be provided as a list')

    base_url = 'https://api.tidbyt.com'
    image_base64 = render_pixlet()

    for device_id in device_ids:
        push_url = f'{base_url}/v0/devices/{device_id}/push'

        headers = {
            'Authorization': f'Bearer {os.environ["TIDBYT_API_KEY"]}'
        }

        body = {
            'image': image_base64,
            'installationID': 'njtbustimes',
            'background': True
        }

        response = requests.post(url=push_url, headers=headers, json=body)
        print(f'Response from Tidbyt: {response.status_code}: {response.text}')
        return response


@scheduler.task('interval', id='tidbyt-push', seconds=60*3, misfire_grace_time=900)
def push():
    print('Running push to Tidbyt')
    push_to_tidbyt(','.split(os.environ['TIDBYT_DEVICE_IDS']))
