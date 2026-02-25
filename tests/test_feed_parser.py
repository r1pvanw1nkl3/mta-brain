from unittest.mock import ANY, MagicMock, patch

import pytest
import requests

from services.subway_live_hydrator import feed_parser
from transit_core.core.exceptions import FeedFetchError, FeedParseError


def test_fetch_raw_feed_success(mock_env_vars):
    """Test successful feed fetch."""
    mock_content = b"invalid-proto-but-ok-for-mock"

    with (
        patch("requests.get") as mock_get,
        patch(
            "services.subway_live_hydrator.feed_parser.FeedMessage"
        ) as MockFeedMessage,
        patch(
            "services.subway_live_hydrator.feed_parser.MessageToDict"
        ) as mock_to_dict,
    ):
        # Configure response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_content
        mock_get.return_value = mock_response

        # Configure Proto parsing
        mock_proto = MagicMock()
        MockFeedMessage.return_value = mock_proto

        expected_dict = {"entity": [{"id": "1"}]}
        mock_to_dict.return_value = expected_dict

        # Execute
        result = feed_parser.fetch_raw_feed("http://fake-url.com")

        # Assert
        mock_get.assert_called_with("http://fake-url.com", timeout=5)  # Default is 5
        mock_proto.ParseFromString.assert_called_with(mock_content)
        mock_to_dict.assert_called_with(
            mock_proto,
            preserving_proto_field_name=True,
            use_integers_for_enums=True,
            descriptor_pool=ANY,
        )
        assert result == expected_dict


def test_fetch_raw_feed_retry_success(mock_env_vars):
    """Test that it retries on failure and eventually succeeds."""
    with (
        patch("requests.get") as mock_get,
        patch("services.subway_live_hydrator.feed_parser.FeedMessage"),
        patch(
            "services.subway_live_hydrator.feed_parser.MessageToDict"
        ) as mock_to_dict,
        patch("time.sleep") as mock_sleep,
    ):
        # First call raises exception, second succeeds
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.content = b"content"

        mock_get.side_effect = [
            requests.ConnectionError,
            mock_response_ok,
            mock_response_ok,
        ]
        mock_to_dict.return_value = {}

        # Execute
        feed_parser.fetch_raw_feed("http://fake-url.com")

        # Assert
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()


def test_fetch_raw_feed_exhausted_retries(mock_env_vars):
    """Test that it raises FeedFetchError after retries are exhausted."""
    with patch("requests.get") as mock_get, patch("time.sleep"):
        mock_get.side_effect = requests.ConnectionError

        with pytest.raises(FeedFetchError):
            feed_parser.fetch_raw_feed("http://fake-url.com")

        # Default retries is 3
        assert mock_get.call_count == 3


def test_validate_feed_success(feed_factory):
    """Test validation with a valid feed dict."""
    feed_model = feed_factory()
    feed_dict = feed_model.model_dump(by_alias=True)

    result = feed_parser.validate_feed(feed_dict)
    assert result == feed_model


def test_validate_feed_failure():
    """Test validation with invalid data."""
    bad_data = {"entity": [{"id": "1", "trip_update": "invalid"}]}

    with pytest.raises(FeedParseError):
        feed_parser.validate_feed(bad_data)
