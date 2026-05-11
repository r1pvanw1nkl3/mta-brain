from transit_core.core.models import Arrival, ArrivalsBoard
from transit_core.messenger.presenters import _minutes_until, present_arrivals_board
from transit_core.messenger.views import Section, Table


def _board(arrivals: list[Arrival]) -> ArrivalsBoard:
    return ArrivalsBoard(
        gtfs_stop_id="635N", stop_name="14 St-Union Sq", arrivals=arrivals
    )


def _arrival(arrival_time: int, **overrides) -> Arrival:
    defaults = dict(
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
