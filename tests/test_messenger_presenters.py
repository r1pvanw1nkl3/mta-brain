from typing import Any

from transit_core.core.models import (
    Arrival,
    ArrivalsBoard,
    Coordinates,
    NearbyStop,
    NearbyStopsResult,
    StopSearchResult,
)
from transit_core.messenger.presenters import (
    _minutes_until,
    present_arrivals_board,
    present_nearby_stops,
    present_stop_search_results,
)
from transit_core.messenger.views import Section, Table


def _board(arrivals: list[Arrival]) -> ArrivalsBoard:
    return ArrivalsBoard(
        gtfs_stop_id="635N", stop_name="14 St-Union Sq", arrivals=arrivals
    )


def _arrival(arrival_time: int, **overrides: Any) -> Arrival:
    defaults: dict[str, Any] = dict(
        trip_id="T1",
        route_id="6",
        headsign="Pelham Bay Park",
        direction="N",
        arrival_time=arrival_time,
        is_realtime=True,
        status="LIVE",
    )
    defaults.update(overrides)
    return Arrival(**defaults)


def test_empty_arrivals_returns_section_with_string_body():
    section = present_arrivals_board(_board([]), now=1_700_000_000)
    assert isinstance(section, Section)
    assert section.body == "No upcoming arrivals."


def test_populated_board_returns_section_with_table():
    now = 1_700_000_000
    section = present_arrivals_board(
        _board([_arrival(now + 180), _arrival(now + 600, route_id="N")]),
        now=now,
    )
    assert isinstance(section, Section)
    assert section.subtitle == "Arrivals for 14 St-Union Sq"

    table = section.body
    assert isinstance(table, Table)
    assert table.headers == ["Route", "Direction", "Destination", "ETA"]
    assert len(table.rows) == 2
    assert table.rows[0] == ["6", "N", "Pelham Bay Park", "3 min"]
    assert table.rows[1] == ["N", "N", "Pelham Bay Park", "10 min"]


def test_missing_headsign_renders_empty_string():
    now = 1_700_000_000
    section = present_arrivals_board(
        _board([_arrival(now + 60, headsign=None)]), now=now
    )
    table = section.body
    assert isinstance(table, Table)
    assert table.rows[0][2] == ""


def test_minutes_until_edges():
    now = 1_700_000_000
    assert _minutes_until(now, now) == "now"
    assert _minutes_until(now - 60, now) == "now"  # past arrival clamps to "now"
    assert _minutes_until(now + 60, now) == "1 min"
    assert _minutes_until(now + 29, now) == "now"  # rounds down to 0
    assert _minutes_until(now + 31, now) == "1 min"  # rounds up to 1


def test_present_stop_search_results_empty():
    section = present_stop_search_results([], "union sq")
    assert isinstance(section, Section)
    assert section.body == "No matching stops."


def test_present_stop_search_results_populated():
    results = [
        StopSearchResult(
            stop_id="635", stop_name="14 St-Union Sq", routes="4,5,6", rank=1
        ),
    ]
    section = present_stop_search_results(results, "union sq")
    assert isinstance(section, Section)
    table = section.body
    assert isinstance(table, Table)
    assert table.headers == ["Stop ID", "Name", "Routes"]
    assert table.rows[0] == ["635", "14 St-Union Sq", "4,5,6"]


def _nearby_stop(stop_id: str, name: str, line: str, dist: float) -> NearbyStop:
    return NearbyStop(
        id=1,
        stop_name=name,
        gtfs_stop_id=stop_id,
        line=line,
        coordinates=Coordinates(lat=40.7, lon=-74.0),
        dist_meters=dist,
    )


def test_present_nearby_stops_none_returns_friendly_message():
    section = present_nearby_stops(None, "9999 Made Up St")
    assert isinstance(section, Section)
    assert section.subtitle is not None
    assert "9999 Made Up St" in section.subtitle
    body = section.body
    assert isinstance(body, str)
    assert "couldn't find" in body.lower()


def test_present_nearby_stops_empty_stops_shows_matched_address():
    result = NearbyStopsResult(matched_address="350 5TH AVE, NEW YORK, NY", stops=[])
    section = present_nearby_stops(result, "350 5th Ave")
    assert isinstance(section, Section)
    assert section.subtitle is not None
    assert "350 5th Ave" in section.subtitle
    assert "350 5TH AVE, NEW YORK, NY" in section.subtitle
    assert section.body == "No subway stops found nearby."


def test_present_nearby_stops_populated_returns_table():
    result = NearbyStopsResult(
        matched_address="350 5TH AVE, NEW YORK, NY",
        stops=[
            _nearby_stop("R20", "34 St-Herald Sq", "BDFM", 123.4),
            _nearby_stop("D17", "34 St-Penn Station", "ACE", 456.7),
        ],
    )
    section = present_nearby_stops(result, "350 5th Ave")
    assert isinstance(section, Section)
    table = section.body
    assert isinstance(table, Table)
    assert table.headers == ["Stop ID", "Name", "Line", "Distance"]
    assert table.rows[0] == ["R20", "34 St-Herald Sq", "BDFM", "123 m"]
    assert table.rows[1] == ["D17", "34 St-Penn Station", "ACE", "456 m"]
