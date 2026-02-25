from unittest.mock import MagicMock, patch

import pytest

from transit_core.api.main import lifespan


@pytest.mark.anyio
async def test_lifespan():
    mock_app = MagicMock()
    mock_redis = MagicMock()
    mock_pool = MagicMock()

    with (
        patch("transit_core.api.main.RedisClient", return_value=mock_redis),
        patch("transit_core.api.main.create_db_pool", return_value=mock_pool),
        patch("transit_core.api.main.RedisStateStore"),
        patch("transit_core.api.main.PostgresStaticStore"),
    ):
        async with lifespan(mock_app):
            assert mock_app.state.state_store is not None
            assert mock_app.state.static_store is not None

        mock_pool.close.assert_called_once()
        mock_redis.client.close.assert_called_once()
