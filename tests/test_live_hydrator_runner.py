from unittest.mock import ANY, MagicMock, patch

import pytest

from services.subway_live_hydrator.runner import runner, worker
from transit_core.core.exceptions import FeedError


@pytest.fixture
def mock_dependencies():
    with (
        patch("services.subway_live_hydrator.runner.settings") as mock_settings,
        patch("services.subway_live_hydrator.feed_parser.fetch_raw_feed") as mock_fetch,
        patch(
            "services.subway_live_hydrator.feed_parser.validate_feed"
        ) as mock_validate,
        patch(
            "services.subway_live_hydrator.state_manager.hydrate_realtime_data"
        ) as mock_hydrate,
        patch("time.sleep") as mock_sleep,
        patch(
            "time.time",
            side_effect=[100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101],
        ),
    ):
        mock_settings.gtfs_live_urls = {"test_key": "http://fake-url.com"}
        mock_settings.redis_gtfs_ttl = 30
        yield {
            "settings": mock_settings,
            "fetch": mock_fetch,
            "validate": mock_validate,
            "hydrate": mock_hydrate,
            "sleep": mock_sleep,
        }


def test_worker_iteration_success(mock_dependencies):
    mock_fetch = mock_dependencies["fetch"]
    mock_validate = mock_dependencies["validate"]
    mock_state_store = MagicMock()

    # Mock return values for one successful iteration
    mock_fetch.return_value = {"header": {"timestamp": 123}}
    mock_state_store.check_and_update_timestamp.return_value = True

    # We need to break the infinite loop in worker
    # One way is to raise an exception after one iteration that we catch in the test
    mock_dependencies["sleep"].side_effect = [None, KeyboardInterrupt]

    with pytest.raises(KeyboardInterrupt):
        worker("test_key", MagicMock(), MagicMock(), mock_state_store)

    mock_fetch.assert_called()
    mock_state_store.check_and_update_timestamp.assert_called_with(ANY, 123)
    mock_validate.assert_called()
    mock_dependencies["hydrate"].assert_called()


def test_worker_iteration_skip_old_timestamp(mock_dependencies):
    mock_fetch = mock_dependencies["fetch"]
    mock_state_store = MagicMock()

    mock_fetch.return_value = {"header": {"timestamp": 123}}
    mock_state_store.check_and_update_timestamp.return_value = False

    mock_dependencies["sleep"].side_effect = [None, KeyboardInterrupt]

    with pytest.raises(KeyboardInterrupt):
        worker("test_key", MagicMock(), MagicMock(), mock_state_store)

    mock_fetch.assert_called()
    mock_dependencies["validate"].assert_not_called()


def test_worker_error_handling(mock_dependencies):
    mock_fetch = mock_dependencies["fetch"]
    mock_fetch.side_effect = FeedError("Fetch failed")

    mock_dependencies["sleep"].side_effect = [None, KeyboardInterrupt]

    with pytest.raises(KeyboardInterrupt):
        worker("test_key", MagicMock(), MagicMock(), MagicMock())

    # Should have slept 10s on error
    mock_dependencies["sleep"].assert_any_call(10)


def test_runner_init(mock_dependencies):
    # Mock RedisClient and other dependencies in runner()
    with (
        patch("transit_core.redis_client.RedisClient"),
        patch("transit_core.infrastructure.state_store.RedisStateStore"),
        patch("transit_core.core.repository.TripWriter"),
        patch("transit_core.core.repository.StopWriter"),
        patch(
            "services.subway_live_hydrator.runner.ThreadPoolExecutor"
        ) as mock_executor,
    ):
        # Break the True loop in runner
        mock_dependencies["sleep"].side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            runner()

        assert mock_executor.called
