"""Integration tests for PostgresStaticStore against a real migrated PostGIS DB.

These cover the DB-specific behaviour that the mock-based unit tests in
``test_static_store.py`` cannot: real PostGIS distance math, ``search_path``
resolution into the ``supplemented`` schema, and pg_trgm fuzzy matching.
"""

import pytest

from transit_core.core.models import Coordinates
from transit_core.db import create_db_pool
from transit_core.infrastructure.static_store import PostgresStaticStore


@pytest.fixture(scope="module")
def db_pool(postgres_container):
    """Real pool built via the production ``create_db_pool`` (so its connection
    setup -- ``search_path = supplemented, public`` -- is exercised too)."""
    pool = create_db_pool(postgres_container.get_connection_url())
    yield pool
    pool.close()


@pytest.fixture
def static_store(db_pool):
    store = PostgresStaticStore(db_pool)
    yield store
    # Reset seeded rows so tests don't bleed into one another.
    with db_pool.connection() as conn:
        conn.execute(
            "TRUNCATE public.subway_entrances, public.stops, public.routes, "
            "public.trips, public.stop_times, supplemented.stops "
            "RESTART IDENTITY CASCADE"
        )
        conn.execute("REFRESH MATERIALIZED VIEW public.mv_station_services")
        conn.commit()


def test_get_nearby_stops_real_postgis(static_store, db_pool):
    with db_pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO public.subway_entrances
                (line, stop_name, gtfs_stop_id, entry_allowed,
                 entrance_latitude, entrance_longitude, entrance_location)
            VALUES
                ('L', 'Close', 'U1', true, 40.7350, -73.9905,
                 ST_SetSRID(ST_MakePoint(-73.9905, 40.7350), 4326)),
                ('L', 'Far', 'U2', true, 40.7450, -73.9805,
                 ST_SetSRID(ST_MakePoint(-73.9805, 40.7450), 4326)),
                ('L', 'Exit only', 'U3', false, 40.7350, -73.9905,
                 ST_SetSRID(ST_MakePoint(-73.9905, 40.7350), 4326))
            """
        )
        conn.commit()

    here = Coordinates(lat=40.7350, lon=-73.9905)
    stops = static_store.get_nearby_stops(here, count=5)

    # entry_allowed = false is filtered out; results ordered by real distance.
    assert [s.gtfs_stop_id for s in stops] == ["U1", "U2"]
    assert stops[0].dist_meters < 1.0  # query point sits on top of U1
    assert stops[0].dist_meters < stops[1].dist_meters
    # The NearbyStop validator folds entrance lat/lon into coordinates.
    assert stops[0].coordinates.lat == pytest.approx(40.7350)
    assert stops[0].coordinates.lon == pytest.approx(-73.9905)
    assert stops[0].line == "L"


def test_get_stop_name_resolves_supplemented_schema(static_store, db_pool):
    # get_stop_name reads the unqualified ``stops`` table, which the pool's
    # search_path resolves to supplemented.stops.
    with db_pool.connection() as conn:
        conn.execute(
            "INSERT INTO supplemented.stops (stop_id, stop_name) VALUES (%s, %s)",
            ("635", "14 St-Union Sq"),
        )
        conn.commit()

    # Platform IDs (635N/635S) are stripped to the parent stop.
    assert static_store.get_stop_name("635N") == "14 St-Union Sq"
    assert static_store.get_stop_name("635") == "14 St-Union Sq"
    assert static_store.get_stop_name("999") == "Unknown"


def test_fuzzy_station_search_pg_trgm(static_store, db_pool):
    with db_pool.connection() as conn:
        # The fuzzy query reads supplemented.stops (via search_path) ...
        conn.execute(
            "INSERT INTO supplemented.stops (stop_id, stop_name, parent_station) "
            "VALUES (%s, %s, NULL)",
            ("UNSQ", "14 St-Union Sq"),
        )
        # ... and LEFT JOINs mv_station_services (public) for the route list,
        # which is built from routes/trips/stop_times/stops.
        conn.execute(
            "INSERT INTO public.stops (stop_id, stop_name, parent_station) VALUES "
            "('UNSQ', '14 St-Union Sq', NULL), ('UNSQ_N', '14 St-Union Sq', 'UNSQ')"
        )
        conn.execute("INSERT INTO public.routes (route_id) VALUES ('L')")
        conn.execute(
            "INSERT INTO public.trips (route_id, trip_id, service_id) "
            "VALUES ('L', 'T1', 'svc')"
        )
        conn.execute(
            "INSERT INTO public.stop_times "
            "(trip_id, stop_id, arrival_time, stop_sequence) "
            "VALUES ('T1', 'UNSQ_N', '08:00:00', 1)"
        )
        conn.execute("REFRESH MATERIALIZED VIEW public.mv_station_services")
        conn.commit()

    # Args mirror how StopReader builds them: a cleaned query + %wrapped% ILIKE.
    results = static_store.fuzzy_station_search("Union Sq", "%Union Sq%", False, None)

    assert len(results) == 1
    assert results[0].stop_id == "UNSQ"
    assert results[0].stop_name == "14 St-Union Sq"
    assert results[0].routes == "L"
