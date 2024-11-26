import csv
import os
import zipfile
import requests
import tempfile
import shutil
from sqlalchemy import create_engine, text

from models import Base, Agency, Stops, CalendarDates, Routes, StopTimes, Trips
from sqlalchemy.orm import sessionmaker

# Environment variables
POSTGRES_URL = os.environ.get('DATABASE_URL')
GTFS_URL = os.environ.get('GTFS_URL')
included_trips = []

if not POSTGRES_URL or not GTFS_URL:
    raise EnvironmentError("Environment variables POSTGRES_URL and GTFS_URL must be set.")


def download_and_extract_gtfs(gtfs_url):
    """Download and extract GTFS zip file."""
    print("Beginning to download GTFS zip.")
    response = requests.get(gtfs_url, stream=True)
    response.raise_for_status()
    print("Completed GTFS zip download.")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "gtfs.zip")

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_dir)

    print("Extracted zip file")
    os.remove(zip_path)  # Remove the zip file after extraction
    return temp_dir


def truncate_tables(engine):
    """Truncate all GTFS-related tables."""
    with engine.connect() as conn:
        # Start a transaction
        with conn.begin():
            # Disable foreign key checks temporarily
            conn.execute(text("SET session_replication_role = 'replica';"))
            try:
                for table in ["agency", "stops", "calendar_dates", "routes", "trips"]:
                    # Truncate each table with RESTART IDENTITY to reset sequences
                    query = text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                    conn.execute(query)
                    print(f"Truncated table {table}")
            finally:
                # Restore foreign key checks
                conn.execute(text("SET session_replication_role = 'origin';"))


def load_gtfs_file_to_db(gtfs_path, table_name, model, session, row_filter=None):
    """Load GTFS data into a specified table."""
    print(f"Loading data to table {table_name}")
    file_path = os.path.join(gtfs_path, f"{table_name}.txt")
    if not os.path.exists(file_path):
        print(f"{table_name}.txt not found, skipping...")
        return

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row_filter and not row_filter(row):
                continue

            # Create a dictionary of column values
            record = model(**{col: row.get(col) for col in model.__table__.columns.keys()})
            session.add(record)

    session.commit()


def record_import(engine, url: str):
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(f"INSERT INTO imports (url) VALUES ('{url}');"))


def main():
    """Main function to process GTFS data."""
    engine = create_engine(POSTGRES_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    Base.metadata.create_all(engine)
    truncate_tables(engine)

    # Download, extract, and process GTFS
    try:
        gtfs_path = download_and_extract_gtfs(GTFS_URL)

        # Load data into each table
        load_gtfs_file_to_db(gtfs_path, "agency", Agency, session)
        load_gtfs_file_to_db(gtfs_path, "stops", Stops, session, stops_filter)
        load_gtfs_file_to_db(gtfs_path, "calendar_dates", CalendarDates, session)
        load_gtfs_file_to_db(gtfs_path, "routes", Routes, session)
        load_gtfs_file_to_db(gtfs_path, "trips", Trips, session, trips_filter)

        # In order to efficiently filter the stop_times import, we need to do a query one time and
        # be able to reference those results within the load_gtfs_file_to_db and stop_times_filters
        # functions.
        global included_trips
        included_trips = {trip_id for (trip_id,) in session.query(Trips.trip_id).all()}
        load_gtfs_file_to_db(gtfs_path, "stop_times", StopTimes, session, stop_times_filter)
    finally:
        if gtfs_path:
            shutil.rmtree(gtfs_path)

    record_import(engine, GTFS_URL)
    session.close()
    print("\n** Load complete! **\n** Exiting container. **")


def trips_filter(row):
    return row['route_id'] in ['21', '237', '234']
    # TODO Refactor to use the route short names instead, which aren't on the trips table


def stops_filter(row):
    return row['stop_code'] in ['20714', '21073', '21055']


def stop_times_filter(row):
    global included_trips
    return row['trip_id'] in included_trips


if __name__ == "__main__":
    main()
