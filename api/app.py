import os
import psycopg2
import pytz
import requests

from datetime import datetime
from flask import Flask, Response, jsonify
from psycopg2 import extras

from .errors import errors

app = Flask(__name__)
# app.register_blueprint(errors)

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
    cur.close()

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
    print('BUS1 NEXT TIMES:', bus1_next_times)
    print('BUS2 NEXT TIMES:', bus2_next_times)

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
    return response.text


def push_to_tidbyt(device_id: str, api_key: str) -> requests.Response:
    """
    Sends the image to Tidbyt
    https://tidbyt.dev/docs/api
    """
    base_url = 'https://api.tidbyt.com'
    image_base64 = render_pixlet()

    print(f'Pushing to device {device_id}')
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

    device_ids = os.environ['TIDBYT_DEVICE_IDS'].split(',')
    api_keys = os.environ['TIDBYT_API_KEYS'].split(',')

    for i, device_id in enumerate(device_ids):
        api_key = api_keys[i]
        push_to_tidbyt(device_id, api_key)  # TODO Refactor so it only hits Axilla once and then pushes to both devices

    return jsonify('Request to push sent to Tidbyt')
