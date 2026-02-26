-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Roles (Running as superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${app_user}') THEN
        EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', '${app_user}', '${app_password}');
    ELSE
        EXECUTE format('ALTER ROLE %I WITH PASSWORD %L', '${app_user}', '${app_password}');
    END IF;
END $$;

-- 3. Base GTFS Tables (Public Schema)
CREATE TABLE IF NOT EXISTS agency (
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT,
    agency_url TEXT,
    agency_timezone TEXT,
    agency_lang TEXT,
    agency_phone TEXT
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    location_type INTEGER,
    parent_station TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    route_id TEXT PRIMARY KEY,
    agency_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    route_desc TEXT,
    route_type INTEGER,
    route_url TEXT,
    route_color TEXT,
    route_text_color TEXT,
    route_sort_order INTEGER
);

CREATE TABLE IF NOT EXISTS calendar (
    service_id TEXT PRIMARY KEY,
    monday INTEGER,
    tuesday INTEGER,
    wednesday INTEGER,
    thursday INTEGER,
    friday INTEGER,
    saturday INTEGER,
    sunday INTEGER,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS calendar_dates (
    service_id TEXT,
    date TEXT,
    exception_type INTEGER,
    PRIMARY KEY (service_id, date)
);

CREATE TABLE IF NOT EXISTS shapes (
    shape_id TEXT,
    shape_pt_sequence INTEGER,
    shape_pt_lat DOUBLE PRECISION,
    shape_pt_lon DOUBLE PRECISION,
    PRIMARY KEY (shape_id, shape_pt_sequence)
);

CREATE TABLE IF NOT EXISTS trips (
    route_id TEXT,
    trip_id TEXT PRIMARY KEY,
    service_id TEXT,
    trip_headsign TEXT,
    direction_id INTEGER,
    shape_id TEXT
);

CREATE TABLE IF NOT EXISTS stop_times (
    trip_id TEXT,
    stop_id TEXT,
    arrival_time INTERVAL,
    departure_time INTERVAL,
    stop_sequence INTEGER,
    PRIMARY KEY (trip_id, stop_sequence)
);

CREATE TABLE IF NOT EXISTS transfers (
    from_stop_id TEXT,
    to_stop_id TEXT,
    transfer_type INTEGER,
    min_transfer_time INTEGER
);

-- 4. Supplemented Schema (Mirroring Public Schema)
CREATE SCHEMA IF NOT EXISTS supplemented;

CREATE TABLE IF NOT EXISTS supplemented.agency (LIKE public.agency INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.stops (LIKE public.stops INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.routes (LIKE public.routes INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.calendar (LIKE public.calendar INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.calendar_dates (LIKE public.calendar_dates INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.shapes (LIKE public.shapes INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.trips (LIKE public.trips INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.stop_times (LIKE public.stop_times INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.transfers (LIKE public.transfers INCLUDING ALL);

-- 5. Materialized Views
CREATE MATERIALIZED VIEW mv_station_services AS
SELECT
    s.parent_station AS stop_id,
    STRING_AGG(DISTINCT r.route_id, ', ' ORDER BY r.route_id) AS routes
FROM trips t
JOIN stop_times st ON t.trip_id = st.trip_id
JOIN stops s ON s.stop_id = st.stop_id
JOIN routes r ON r.route_id = t.route_id
WHERE s.parent_station IS NOT NULL
GROUP BY s.parent_station;

-- 6. Indexes
CREATE INDEX idx_stops_parent ON stops (parent_station);
CREATE INDEX idx_trips_route ON trips (route_id);
CREATE INDEX idx_trips_service ON trips (service_id);
CREATE INDEX idx_stop_times_stop_id ON stop_times (stop_id);
CREATE INDEX idx_stop_times_trip_id ON stop_times (trip_id);
CREATE UNIQUE INDEX idx_mv_station_services_stop_id ON mv_station_services (stop_id);

CREATE INDEX IF NOT EXISTS trgm_idx_stops_clean_name
ON stops
USING gin (REPLACE(stop_name, '-', ' ') gin_trgm_ops);

-- 7. Permissions & Grants
GRANT CONNECT ON DATABASE mta_brain TO ${app_user};
