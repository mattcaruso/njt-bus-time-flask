from sqlalchemy import Column, String, Integer, Float, Date
from sqlalchemy.ext.declarative import declarative_base

# Base for SQLAlchemy models
Base = declarative_base()

# Define GTFS table models
class Agency(Base):
    __tablename__ = 'agency'
    agency_id = Column(String, primary_key=True)
    agency_name = Column(String, nullable=False)
    agency_url = Column(String, nullable=False)
    agency_timezone = Column(String, nullable=False)
    agency_lang = Column(String)
    agency_phone = Column(String)
    agency_fare_url = Column(String)
    agency_email = Column(String)

class Stops(Base):
    __tablename__ = 'stops'
    stop_id = Column(String, primary_key=True)
    stop_name = Column(String, nullable=False)
    stop_lat = Column(Float, nullable=False)
    stop_lon = Column(Float, nullable=False)
    stop_code = Column(String)
    stop_desc = Column(String)
    zone_id = Column(String)
    stop_url = Column(String)
    location_type = Column(Integer)
    parent_station = Column(String)
    stop_timezone = Column(String)
    wheelchair_boarding = Column(Integer)

class CalendarDates(Base):
    __tablename__ = 'calendar_dates'
    service_id = Column(String, primary_key=True)
    date = Column(Date, primary_key=True)
    exception_type = Column(Integer, nullable=False)

class Routes(Base):
    __tablename__ = 'routes'
    route_id = Column(String, primary_key=True)
    agency_id = Column(String)
    route_short_name = Column(String)
    route_long_name = Column(String)
    route_desc = Column(String)
    route_type = Column(Integer, nullable=False)
    route_url = Column(String)
    route_color = Column(String)
    route_text_color = Column(String)

class StopTimes(Base):
    __tablename__ = 'stop_times'
    trip_id = Column(String, primary_key=True)
    arrival_time = Column(String)
    departure_time = Column(String)
    stop_id = Column(String, primary_key=True)
    stop_sequence = Column(Integer, primary_key=True)
    stop_headsign = Column(String)
    pickup_type = Column(Integer)
    drop_off_type = Column(Integer)
    shape_dist_traveled = Column(Float)
    timepoint = Column(Integer)

class Trips(Base):
    __tablename__ = 'trips'
    route_id = Column(String)
    service_id = Column(String)
    trip_id = Column(String, primary_key=True)
    trip_headsign = Column(String)
    trip_short_name = Column(String)
    direction_id = Column(Integer)
    block_id = Column(String)
    shape_id = Column(String)
    wheelchair_accessible = Column(Integer)
    bikes_allowed = Column(Integer)