CREATE TABLE IF NOT EXISTS agency (
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT,
    agency_url TEXT,
    agency_timezone TEXT,
    agency_lang TEXT,
    agency_phone TEXT
);

-- 2. Stops
CREATE TABLE IF NOT EXISTS stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    location_type INTEGER,
    parent_station TEXT
);

-- 3. Routes
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

-- 4. Calendar (Schedules)
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

-- 5. Calendar Dates (Exceptions)
CREATE TABLE IF NOT EXISTS calendar_dates (
    service_id TEXT,
    date TEXT,
    exception_type INTEGER,
    PRIMARY KEY (service_id, date)
);

-- 6. Shapes (Geometry)
CREATE TABLE IF NOT EXISTS shapes (
    shape_id TEXT,
    shape_pt_sequence INTEGER,
    shape_pt_lat DOUBLE PRECISION,
    shape_pt_lon DOUBLE PRECISION,
    PRIMARY KEY (shape_id, shape_pt_sequence)
);

-- 7. Trips
CREATE TABLE IF NOT EXISTS trips (
    route_id TEXT,
    trip_id TEXT PRIMARY KEY,
    service_id TEXT,
    trip_headsign TEXT,
    direction_id INTEGER,
    shape_id TEXT
);

-- 8. Stop Times (The heavy data)
CREATE TABLE IF NOT EXISTS stop_times (
    trip_id TEXT,
    stop_id TEXT,
    arrival_time TEXT,
    departure_time TEXT,
    stop_sequence INTEGER,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- 9. Transfers
CREATE TABLE IF NOT EXISTS transfers (
    from_stop_id TEXT,
    to_stop_id TEXT,
    transfer_type INTEGER,
    min_transfer_time INTEGER
);

-- --- INDEXES (For Performance) ---
-- These are critical for linking tables efficiently.

CREATE INDEX idx_stops_parent ON stops (parent_station);
CREATE INDEX idx_trips_route ON trips (route_id);
CREATE INDEX idx_trips_service ON trips (service_id);
CREATE INDEX idx_stop_times_stop_id ON stop_times (stop_id);
CREATE INDEX idx_stop_times_trip_id ON stop_times (trip_id);
