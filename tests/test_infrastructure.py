import time
from unittest.mock import MagicMock

from transit_core.infrastructure.state_store import RedisStateStore


def test_redis_state_store_batch_session():
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    # Mock the context manager
    mock_redis.pipeline_scope.return_value.__enter__.return_value = mock_pipe

    store = RedisStateStore(redis_client=mock_redis)

    # Outside batch session, _get_client should return redis.client
    assert store._get_client() == mock_redis.client

    with store.batch_session():
        # Inside batch session, _get_client should return the pipe
        assert store._get_client() == mock_pipe
        store.set_kv("test_key", "test_value", 3600)
        mock_pipe.set.assert_called_once_with("test_key", "test_value", ex=3600)

    # After batch session, it should be back to redis.client
    assert store._get_client() == mock_redis.client


def test_redis_state_store_set_kv():
    mock_redis = MagicMock()
    store = RedisStateStore(redis_client=mock_redis)
    store.set_kv("k", "v", 100)
    mock_redis.client.set.assert_called_once_with("k", "v", ex=100)


def test_redis_state_store_get_kv():
    mock_redis = MagicMock()
    mock_redis.client.get.return_value = "value"
    store = RedisStateStore(redis_client=mock_redis)
    assert store.get_kv("k") == "value"
    mock_redis.client.get.assert_called_once_with("k")


def test_redis_state_store_sync_set():
    current_time = int(time.time())
    mock_redis = MagicMock()
    store = RedisStateStore(redis_client=mock_redis)
    mapping = {"a": 1, "b": 2}
    store.sync_set("key", mapping, current_time, 500)

    mock_redis.client.zremrangebyscore.assert_called_once_with("key", 0, current_time)
    mock_redis.client.zadd.assert_called_once_with("key", mapping)
    mock_redis.client.expire.assert_called_once_with("key", 500)


def test_redis_state_store_get_zset():
    mock_redis = MagicMock()
    mock_redis.client.zrange.return_value = [("a", 1.0), ("b", 2.0)]
    store = RedisStateStore(redis_client=mock_redis)
    assert store.get_zset("key") == {"a": 1, "b": 2}
    mock_redis.client.zrange.assert_called_once_with("key", 0, -1, withscores=True)


def test_redis_state_store_check_and_update_timestamp():
    mock_redis = MagicMock()
    store = RedisStateStore(redis_client=mock_redis)

    # Case 1: Stale timestamp
    mock_redis.client.get.return_value = "1000"
    assert store.check_and_update_timestamp("key", 500) is False
    mock_redis.client.set.assert_not_called()

    # Case 2: New timestamp
    mock_redis.client.get.return_value = "1000"
    assert store.check_and_update_timestamp("key", 1500) is True
    mock_redis.client.set.assert_called_once_with("key", 1500)

    # Case 3: No previous timestamp
    mock_redis.client.set.reset_mock()
    mock_redis.client.get.return_value = None
    assert store.check_and_update_timestamp("key", 500) is True
    mock_redis.client.set.assert_called_once_with("key", 500)
