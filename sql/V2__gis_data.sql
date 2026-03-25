CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE subway_entrances (
    id SERIAL PRIMARY KEY,
    division TEXT,
    line TEXT,
    borough TEXT,
    stop_name TEXT,
    complex_id TEXT,
    constituent_station_name TEXT,
    station_id TEXT,
    gtfs_stop_id TEXT,
    daytime_routes TEXT,
    entrance_type TEXT,
    entry_allowed BOOLEAN,
    exit_allowed BOOLEAN,
    entrance_latitude DOUBLE PRECISION,
    entrance_longitude DOUBLE PRECISION,
    entrance_location GEOMETRY(Point, 4326)
);

CREATE INDEX idx_subway_entrance_geom ON subway_entrances USING GIST (entrance_location);
