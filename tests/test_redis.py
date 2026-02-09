from unittest.mock import MagicMock, patch

import pytest
import redis

from transit_core.core.exceptions import CacheError
from transit_core.redis_client import RedisClient


def test_redis_client_init():
    with patch("redis.ConnectionPool") as mock_pool, patch("redis.Redis") as mock_redis:
        client = RedisClient(host="fake-host", port=1234, db=1)
        mock_pool.assert_called_once_with(
            host="fake-host", port=1234, db=1, decode_responses=True, max_connections=20
        )
        assert client.client == mock_redis.return_value


def test_pipeline_scope_success():
    mock_redis_instance = MagicMock()
    mock_pipe = MagicMock()
    mock_redis_instance.pipeline.return_value = mock_pipe

    with patch("redis.Redis", return_value=mock_redis_instance):
        client = RedisClient()
        with client.pipeline_scope() as pipe:
            pipe.set("key", "value")

        mock_pipe.execute.assert_called_once()


def test_pipeline_scope_redis_error():
    mock_redis_instance = MagicMock()
    mock_pipe = MagicMock()
    mock_redis_instance.pipeline.return_value = mock_pipe
    mock_pipe.execute.side_effect = redis.RedisError("Execution failed")

    with patch("redis.Redis", return_value=mock_redis_instance):
        client = RedisClient()
        with pytest.raises(CacheError) as excinfo:
            with client.pipeline_scope() as _:
                pass

        assert "Redis pipeline failed" in str(excinfo.value)
        mock_pipe.reset.assert_called_once()


def test_pipeline_scope_unexpected_error():
    mock_redis_instance = MagicMock()
    mock_pipe = MagicMock()
    mock_redis_instance.pipeline.return_value = mock_pipe

    with patch("redis.Redis", return_value=mock_redis_instance):
        client = RedisClient()
        with pytest.raises(ValueError, match="Boom"):
            with client.pipeline_scope() as _:
                raise ValueError("Boom")

        mock_pipe.reset.assert_called_once()
        mock_pipe.execute.assert_not_called()
