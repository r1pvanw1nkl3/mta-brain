from unittest.mock import AsyncMock, MagicMock

from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.models import (
    ArrivalsBoard,
    NearbyArrivalsResult,
    NearbyStopsResult,
)
from transit_core.core.repository import StopReader
from transit_core.messenger.handler import Handler
from transit_core.messenger.models import Message
from transit_core.messenger.views import Section


def _empty_board() -> ArrivalsBoard:
    return ArrivalsBoard(gtfs_stop_id="635N", stop_name="14 St", arrivals=[])


async def test_handle_non_command_returns_none():
    handler = Handler(
        stop_reader=MagicMock(spec=StopReader),
        planner=MagicMock(spec=PlannerEngine),
    )
    assert await handler.handle("hello", "user-1") is None


async def test_handle_parse_error_returns_message_with_error_text():
    handler = Handler(
        stop_reader=MagicMock(spec=StopReader),
        planner=MagicMock(spec=PlannerEngine),
    )
    msg = await handler.handle("!arrivals", "user-1")
    assert isinstance(msg, Message)
    assert msg.receiver_id == "user-1"
    assert isinstance(msg.body, str)
    assert "stop_id" in msg.body


async def test_handle_arrivals_calls_reader_and_returns_section():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_arrivals_board.return_value = _empty_board()

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!arrivals 635N", "user-1")

    mock_reader.get_arrivals_board.assert_called_once_with("635N", get_schedules=False)
    assert isinstance(msg, Message)
    assert msg.receiver_id == "user-1"
    assert isinstance(msg.body, Section)


async def test_handle_search_calls_reader_and_returns_section():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.fuzzy_station_search.return_value = []

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!search union square", "user-1")

    mock_reader.fuzzy_station_search.assert_called_once_with("union square")
    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)


async def test_handle_nearby_calls_reader_with_normalized_address():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_stops_near_address = AsyncMock(
        return_value=NearbyStopsResult(
            matched_address="350 5TH AVE, NEW YORK, NY", stops=[]
        )
    )

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!nearby 350 5th Ave", "user-1")

    mock_reader.get_stops_near_address.assert_awaited_once_with(
        "350 5th Ave, New York, NY", 5
    )
    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)


async def test_handle_nearby_with_bare_queens_returns_normalization_error_message():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_stops_near_address = AsyncMock()

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!nearby 60-40 68th Rd Queens", "user-1")

    mock_reader.get_stops_near_address.assert_not_awaited()
    assert isinstance(msg, Message)
    assert msg.receiver_id == "user-1"
    assert isinstance(msg.body, str)
    assert "neighborhood" in msg.body.lower()


async def test_handle_nearby_uses_original_query_in_subtitle():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_stops_near_address = AsyncMock(
        return_value=NearbyStopsResult(
            matched_address="350 5TH AVE, NEW YORK, NY", stops=[]
        )
    )

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!nearby 350 5th Ave", "user-1")

    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)
    # Original (un-normalized) query should appear in the subtitle.
    assert msg.body.subtitle is not None
    assert "350 5th Ave" in msg.body.subtitle


async def test_handle_nearby_geocode_miss_returns_friendly_section():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_stops_near_address = AsyncMock(return_value=None)

    handler = Handler(stop_reader=mock_reader, planner=MagicMock(spec=PlannerEngine))
    msg = await handler.handle("!nearby 9999 Made Up St Brooklyn", "user-1")

    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)
    body = msg.body.body
    assert isinstance(body, str)
    assert "couldn't find" in body.lower() or "could not find" in body.lower()


async def test_handle_planner_calls_engine_with_normalized_address():
    mock_planner = MagicMock(spec=PlannerEngine)
    mock_planner.get_arrivals_by_address = AsyncMock(
        return_value=NearbyArrivalsResult(
            matched_address="350 5TH AVE, NEW YORK, NY", arrivals=[]
        )
    )

    handler = Handler(stop_reader=MagicMock(spec=StopReader), planner=mock_planner)
    msg = await handler.handle("!planner 350 5th Ave", "user-1")

    mock_planner.get_arrivals_by_address.assert_awaited_once()
    awaited_args = mock_planner.get_arrivals_by_address.await_args
    assert awaited_args is not None
    assert awaited_args.args[0] == "350 5th Ave, New York, NY"
    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)


async def test_handle_planner_bare_queens_returns_normalization_error_message():
    mock_planner = MagicMock(spec=PlannerEngine)
    mock_planner.get_arrivals_by_address = AsyncMock()

    handler = Handler(stop_reader=MagicMock(spec=StopReader), planner=mock_planner)
    msg = await handler.handle("!planner 60-40 68th Rd Queens", "user-1")

    mock_planner.get_arrivals_by_address.assert_not_awaited()
    assert isinstance(msg, Message)
    assert isinstance(msg.body, str)
    assert "neighborhood" in msg.body.lower()


async def test_handle_planner_geocode_miss_returns_friendly_section():
    mock_planner = MagicMock(spec=PlannerEngine)
    mock_planner.get_arrivals_by_address = AsyncMock(return_value=None)

    handler = Handler(stop_reader=MagicMock(spec=StopReader), planner=mock_planner)
    msg = await handler.handle("!planner 9999 Made Up St", "user-1")

    assert isinstance(msg, Message)
    assert isinstance(msg.body, Section)
    body = msg.body.body
    assert isinstance(body, str)
    assert "couldn't find" in body.lower()
