"""
Unit tests for Redis Distributed Locks
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from redis.exceptions import RedisError

from carpeta_common.redis_lock import (
    RedisLock,
    LockAcquisitionError,
    LockReleaseError,
    LockManager
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    client = Mock()
    client.set = Mock(return_value=True)
    client.get = Mock(return_value=b"test-token")
    client.expire = Mock(return_value=True)
    client.register_script = Mock(return_value=Mock(return_value=1))
    return client


def test_lock_acquisition_success(mock_redis):
    """Test successful lock acquisition."""
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    
    assert lock.acquire() is True
    assert lock.is_locked() is True
    
    # Verify Redis SET NX EX was called
    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "lock:test_resource"
    assert call_args[1]["nx"] is True
    assert call_args[1]["ex"] == 30


def test_lock_acquisition_failure(mock_redis):
    """Test lock acquisition failure (resource already locked)."""
    mock_redis.set.return_value = False
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30, blocking=False)
    
    assert lock.acquire() is False
    assert lock.is_locked() is False


def test_lock_release_success(mock_redis):
    """Test successful lock release."""
    # Mock Lua script execution
    release_script = Mock(return_value=1)  # 1 = deleted
    mock_redis.register_script.return_value = release_script
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    lock.acquire()
    
    assert lock.release() is True
    assert lock.is_locked() is False
    
    # Verify Lua script was called
    release_script.assert_called_once()


def test_lock_release_not_owned(mock_redis):
    """Test lock release when not owned (expired or stolen)."""
    # Mock Lua script returning 0 (not deleted)
    release_script = Mock(return_value=0)
    mock_redis.register_script.return_value = release_script
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    lock.acquire()
    
    assert lock.release() is False


def test_lock_release_without_acquisition(mock_redis):
    """Test releasing lock that was never acquired."""
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    
    # Don't acquire, just try to release
    assert lock.release() is False


def test_lock_extend_success(mock_redis):
    """Test lock TTL extension."""
    mock_redis.get.return_value = b"test-token"
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    lock.token = "test-token"  # Match the mocked return value
    lock.acquire()
    
    assert lock.extend(additional_time=60) is True
    
    # Verify expire was called
    mock_redis.expire.assert_called_once_with("lock:test_resource", 60)


def test_lock_extend_not_owned(mock_redis):
    """Test extending lock that's not owned."""
    mock_redis.get.return_value = b"different-token"
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    lock.acquire()
    
    assert lock.extend() is False


def test_context_manager_success(mock_redis):
    """Test lock with context manager (success)."""
    release_script = Mock(return_value=1)
    mock_redis.register_script.return_value = release_script
    
    with RedisLock(mock_redis, "test_resource", ttl=30) as lock:
        assert lock.is_locked() is True
    
    # Lock should be released after context
    assert lock.is_locked() is False
    release_script.assert_called_once()


def test_context_manager_acquisition_failure(mock_redis):
    """Test context manager raises when lock can't be acquired."""
    mock_redis.set.return_value = False
    
    with pytest.raises(LockAcquisitionError):
        with RedisLock(mock_redis, "test_resource", ttl=30):
            pass


def test_blocking_acquisition_timeout(mock_redis):
    """Test blocking acquisition with timeout."""
    mock_redis.set.return_value = False  # Always fail
    
    lock = RedisLock(
        mock_redis,
        "test_resource",
        ttl=30,
        blocking=True,
        blocking_timeout=0.2,
        retry_interval=0.05
    )
    
    start = time.time()
    result = lock.acquire()
    elapsed = time.time() - start
    
    assert result is False
    assert elapsed >= 0.2
    assert elapsed < 0.5  # Shouldn't wait too long


def test_redis_error_during_acquisition(mock_redis):
    """Test handling Redis errors during acquisition."""
    mock_redis.set.side_effect = RedisError("Connection failed")
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    
    with pytest.raises(LockAcquisitionError):
        lock.acquire()


def test_redis_error_during_release(mock_redis):
    """Test handling Redis errors during release."""
    release_script = Mock(side_effect=RedisError("Connection failed"))
    mock_redis.register_script.return_value = release_script
    
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    lock.acquire()
    
    with pytest.raises(LockReleaseError):
        lock.release()


def test_lock_manager_document(mock_redis):
    """Test LockManager document locking."""
    release_script = Mock(return_value=1)
    mock_redis.register_script.return_value = release_script
    
    manager = LockManager(mock_redis)
    
    with manager.lock_document("doc-123") as lock:
        assert lock.is_locked() is True
        assert "document:doc-123" in lock.key
    
    # Lock released after context
    assert lock.is_locked() is False


def test_lock_manager_transfer(mock_redis):
    """Test LockManager transfer locking."""
    release_script = Mock(return_value=1)
    mock_redis.register_script.return_value = release_script
    
    manager = LockManager(mock_redis)
    
    with manager.lock_transfer("transfer-456", ttl=60) as lock:
        assert lock.is_locked() is True
        assert "transfer:transfer-456" in lock.key
        assert lock.ttl == 60


def test_lock_manager_user_operation(mock_redis):
    """Test LockManager user operation locking."""
    release_script = Mock(return_value=1)
    mock_redis.register_script.return_value = release_script
    
    manager = LockManager(mock_redis)
    
    with manager.lock_user_operation("user-789", "update_profile") as lock:
        assert lock.is_locked() is True
        assert "user:user-789:update_profile" in lock.key


def test_lock_manager_try_lock_success(mock_redis):
    """Test LockManager non-blocking try_lock (success)."""
    release_script = Mock(return_value=1)
    mock_redis.register_script.return_value = release_script
    
    manager = LockManager(mock_redis)
    
    lock = manager.try_lock("my_resource")
    assert lock is not None
    assert lock.is_locked() is True
    
    lock.release()


def test_lock_manager_try_lock_failure(mock_redis):
    """Test LockManager non-blocking try_lock (failure)."""
    mock_redis.set.return_value = False
    
    manager = LockManager(mock_redis)
    
    lock = manager.try_lock("my_resource")
    assert lock is None


def test_unique_tokens():
    """Test that each lock instance has a unique token."""
    mock_redis = Mock()
    
    lock1 = RedisLock(mock_redis, "resource", ttl=30)
    lock2 = RedisLock(mock_redis, "resource", ttl=30)
    
    assert lock1.token != lock2.token


def test_lock_repr():
    """Test RedisLock string representation."""
    mock_redis = Mock()
    lock = RedisLock(mock_redis, "test_resource", ttl=30)
    
    repr_str = repr(lock)
    assert "test_resource" in repr_str
    assert "locked=False" in repr_str
    assert "ttl=30" in repr_str

