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

CREATE UNIQUE INDEX idx_mv_station_services_stop_id ON mv_station_services (stop_id);
