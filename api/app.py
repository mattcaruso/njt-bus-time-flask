import os
import psycopg2
import pytz

from datetime import datetime
from flask import Flask, Response, jsonify
from psycopg2 import extras

from .errors import errors

app = Flask(__name__)
app.register_blueprint(errors)


conn = psycopg2.connect(
        host=os.environ['PGHOST'],
        port=os.environ['PGPORT'],
        database=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD']
)


@app.route("/")
def index():
    return Response("Hello, world!", status=200)


@app.route("/stops/<stop_code>/<route_name>/next_departures", methods=["GET"])
def next_departures(stop_code, route_name):
    # Open a cursor to perform database operations
    cur = conn.cursor(cursor_factory=extras.DictCursor)

    now = datetime.now(pytz.timezone('America/New_York'))
    weekday = now.weekday()

    if weekday == 5:    # Saturday
        service_id = 1
    elif weekday == 6:  # Sunday
        service_id = 2
    else:               # Weekdays
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
        pretty_time = local_time.strftime('%-I:%M %p')
        response.append(pretty_time)

    # cur.close()

    return jsonify()


@app.route("/health")
def health():
    return Response("OK", status=200)
