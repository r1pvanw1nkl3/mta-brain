from unittest.mock import MagicMock

from transit_core.core.models import ArrivalsBoard
from transit_core.core.repository import StopReader
from transit_core.messenger.handler import Handler
from transit_core.messenger.models import Message
from transit_core.messenger.views import Section


def _empty_board() -> ArrivalsBoard:
    return ArrivalsBoard(gtfs_stop_id="635N", stop_name="14 St", arrivals=[])


def test_handle_non_command_returns_none():
    handler = Handler(stop_reader=MagicMock(spec=StopReader))
    assert handler.handle("hello", "user-1") is None


def test_handle_parse_error_returns_message_with_error_text():
    handler = Handler(stop_reader=MagicMock(spec=StopReader))
    msg = handler.handle("!arrivals", "user-1")
    assert isinstance(msg, Message)
    assert msg.receiver_id == "user-1"
    assert isinstance(msg.body, str)
    assert "stop_id" in msg.body


def test_handle_arrivals_calls_reader_and_returns_section():
    mock_reader = MagicMock(spec=StopReader)
    mock_reader.get_arrivals_board.return_value = _empty_board()

    handler = Handler(stop_reader=mock_reader)
    msg = handler.handle("!arrivals 635N", "user-1")

    mock_reader.get_arrivals_board.assert_called_once_with("635N", get_schedules=False)
    assert isinstance(msg, Message)
    assert msg.receiver_id == "user-1"
    assert isinstance(msg.body, Section)
