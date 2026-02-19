CREATE INDEX IF NOT EXISTS trgm_idx_stops_clean_name
ON stops
USING gin (REPLACE(stop_name, '-', ' ') gin_trgm_ops);
