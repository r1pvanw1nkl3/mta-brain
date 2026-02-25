from unittest.mock import MagicMock

from transit_core.api.dependencies import get_stop_reader, get_trip_reader


def test_get_stop_reader():
    mock_request = MagicMock()
    mock_request.app.state.state_store = MagicMock()
    mock_request.app.state.static_store = MagicMock()

    reader = get_stop_reader(mock_request)
    assert reader is not None


def test_get_trip_reader():
    mock_request = MagicMock()
    mock_request.app.state.state_store = MagicMock()
    mock_request.app.state.static_store = MagicMock()

    reader = get_trip_reader(mock_request)
    assert reader is not None
