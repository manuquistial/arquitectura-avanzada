"""
Redis Distributed Locks
Provides distributed locking mechanism using Redis for coordination across services
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, AsyncGenerator, Generator

import redis.asyncio as aioredis
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisLockError(Exception):
    """Base exception for Redis lock errors"""
    pass


class LockAcquisitionError(RedisLockError):
    """Raised when lock cannot be acquired"""
    pass


class LockReleaseError(RedisLockError):
    """Raised when lock cannot be released"""
    pass


class RedisLock:
    """
    Distributed lock implementation using Redis.
    
    Features:
    - Atomic lock acquisition (SET NX EX)
    - Safe lock release (Lua script to verify ownership)
    - TTL to prevent deadlocks
    - Auto-renewal for long operations
    - Context manager support
    
    Usage:
        # Synchronous
        lock = RedisLock(redis_client, "my_resource", ttl=30)
        if lock.acquire():
            try:
                # Critical section
                pass
            finally:
                lock.release()
        
        # With context manager
        with RedisLock(redis_client, "my_resource"):
            # Critical section
            pass
    """
    
    # Lua script for safe lock release (atomic check + delete)
    RELEASE_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    
    def __init__(
        self,
        redis_client: Redis,
        resource: str,
        ttl: int = 30,
        blocking: bool = False,
        blocking_timeout: Optional[float] = None,
        retry_interval: float = 0.1
    ):
        """
        Initialize Redis lock.
        
        Args:
            redis_client: Redis client instance
            resource: Name of resource to lock
            ttl: Lock TTL in seconds (default: 30s)
            blocking: If True, wait for lock acquisition
            blocking_timeout: Max time to wait (None = forever)
            retry_interval: Time between acquisition attempts
        """
        self.redis = redis_client
        self.resource = resource
        self.ttl = ttl
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.retry_interval = retry_interval
        
        # Unique token to identify this lock instance
        self.token = str(uuid.uuid4())
        
        # Lock key in Redis
        self.key = f"lock:{resource}"
        
        # Track if lock is held
        self._locked = False
        
        # Compile Lua script
        self._release_script = self.redis.register_script(self.RELEASE_SCRIPT)
    
    def acquire(self, blocking: Optional[bool] = None, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.
        
        Args:
            blocking: Override instance blocking setting
            timeout: Override instance blocking_timeout
        
        Returns:
            True if lock acquired, False otherwise
        
        Raises:
            LockAcquisitionError: If error during acquisition
        """
        blocking = blocking if blocking is not None else self.blocking
        timeout = timeout if timeout is not None else self.blocking_timeout
        
        start_time = time.time()
        
        while True:
            try:
                # Atomic SET NX EX (set if not exists with expiration)
                acquired = self.redis.set(
                    self.key,
                    self.token,
                    nx=True,  # Only set if key doesn't exist
                    ex=self.ttl  # Set expiration
                )
                
                if acquired:
                    self._locked = True
                    logger.debug(f"Lock acquired: {self.key} (token: {self.token}, ttl: {self.ttl}s)")
                    return True
                
                # Lock not acquired
                if not blocking:
                    logger.debug(f"Lock acquisition failed (non-blocking): {self.key}")
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning(f"Lock acquisition timeout: {self.key} (waited {elapsed:.2f}s)")
                        return False
                
                # Wait before retry
                time.sleep(self.retry_interval)
                
            except RedisError as e:
                logger.error(f"Redis error during lock acquisition: {e}")
                raise LockAcquisitionError(f"Failed to acquire lock: {e}")
    
    def release(self) -> bool:
        """
        Release the lock.
        
        Only releases if this instance owns the lock (verified by token).
        
        Returns:
            True if lock released, False if lock not owned
        
        Raises:
            LockReleaseError: If error during release
        """
        if not self._locked:
            logger.debug(f"Lock not held, skipping release: {self.key}")
            return False
        
        try:
            # Use Lua script for atomic check + delete
            result = self._release_script(keys=[self.key], args=[self.token])
            
            if result == 1:
                self._locked = False
                logger.debug(f"Lock released: {self.key} (token: {self.token})")
                return True
            else:
                # Lock expired or stolen
                logger.warning(f"Lock release failed (not owned): {self.key}")
                self._locked = False
                return False
        
        except RedisError as e:
            logger.error(f"Redis error during lock release: {e}")
            raise LockReleaseError(f"Failed to release lock: {e}")
    
    def extend(self, additional_time: Optional[int] = None) -> bool:
        """
        Extend lock TTL.
        
        Args:
            additional_time: Seconds to add (default: original TTL)
        
        Returns:
            True if extended, False otherwise
        """
        if not self._locked:
            logger.warning(f"Cannot extend lock (not held): {self.key}")
            return False
        
        additional_time = additional_time or self.ttl
        
        try:
            # Check ownership and extend
            current_value = self.redis.get(self.key)
            if current_value and current_value.decode() == self.token:
                self.redis.expire(self.key, additional_time)
                logger.debug(f"Lock extended: {self.key} (+{additional_time}s)")
                return True
            else:
                logger.warning(f"Lock extend failed (not owned): {self.key}")
                self._locked = False
                return False
        
        except RedisError as e:
            logger.error(f"Redis error during lock extend: {e}")
            return False
    
    def is_locked(self) -> bool:
        """Check if this instance holds the lock."""
        return self._locked
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise LockAcquisitionError(f"Could not acquire lock: {self.key}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
    
    def __repr__(self):
        return f"RedisLock(resource={self.resource}, locked={self._locked}, ttl={self.ttl})"


class AsyncRedisLock:
    """
    Async version of RedisLock for use with asyncio.
    
    Usage:
        async with AsyncRedisLock(redis_client, "my_resource"):
            # Critical section
            pass
    """
    
    RELEASE_SCRIPT = RedisLock.RELEASE_SCRIPT
    
    def __init__(
        self,
        redis_client: aioredis.Redis,
        resource: str,
        ttl: int = 30,
        blocking: bool = False,
        blocking_timeout: Optional[float] = None,
        retry_interval: float = 0.1
    ):
        self.redis = redis_client
        self.resource = resource
        self.ttl = ttl
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.retry_interval = retry_interval
        
        self.token = str(uuid.uuid4())
        self.key = f"lock:{resource}"
        self._locked = False
        
        # Lua script will be registered on first use
        self._release_script = None
    
    async def _ensure_script(self):
        """Lazy load Lua script."""
        if self._release_script is None:
            self._release_script = self.redis.register_script(self.RELEASE_SCRIPT)
    
    async def acquire(self, blocking: Optional[bool] = None, timeout: Optional[float] = None) -> bool:
        """Async acquire lock."""
        blocking = blocking if blocking is not None else self.blocking
        timeout = timeout if timeout is not None else self.blocking_timeout
        
        start_time = time.time()
        
        while True:
            try:
                acquired = await self.redis.set(
                    self.key,
                    self.token,
                    nx=True,
                    ex=self.ttl
                )
                
                if acquired:
                    self._locked = True
                    logger.debug(f"Lock acquired (async): {self.key}")
                    return True
                
                if not blocking:
                    return False
                
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                
                # Use asyncio.sleep for async wait
                import asyncio
                await asyncio.sleep(self.retry_interval)
                
            except RedisError as e:
                logger.error(f"Redis error during async lock acquisition: {e}")
                raise LockAcquisitionError(f"Failed to acquire lock: {e}")
    
    async def release(self) -> bool:
        """Async release lock."""
        if not self._locked:
            return False
        
        try:
            await self._ensure_script()
            result = await self._release_script(keys=[self.key], args=[self.token])
            
            if result == 1:
                self._locked = False
                logger.debug(f"Lock released (async): {self.key}")
                return True
            else:
                logger.warning(f"Lock release failed (async, not owned): {self.key}")
                self._locked = False
                return False
        
        except RedisError as e:
            logger.error(f"Redis error during async lock release: {e}")
            raise LockReleaseError(f"Failed to release lock: {e}")
    
    async def extend(self, additional_time: Optional[int] = None) -> bool:
        """Async extend lock."""
        if not self._locked:
            return False
        
        additional_time = additional_time or self.ttl
        
        try:
            current_value = await self.redis.get(self.key)
            if current_value and current_value.decode() == self.token:
                await self.redis.expire(self.key, additional_time)
                logger.debug(f"Lock extended (async): {self.key}")
                return True
            else:
                self._locked = False
                return False
        
        except RedisError as e:
            logger.error(f"Redis error during async lock extend: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not await self.acquire():
            raise LockAcquisitionError(f"Could not acquire lock: {self.key}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


class LockManager:
    """
    High-level lock manager for common patterns.
    
    Provides convenience methods for typical locking scenarios.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    @contextmanager
    def lock_document(self, document_id: str, ttl: int = 30) -> Generator[RedisLock, None, None]:
        """
        Lock a document for exclusive access.
        
        Usage:
            with lock_manager.lock_document("doc-123"):
                # Update document
                pass
        """
        lock = RedisLock(self.redis, f"document:{document_id}", ttl=ttl, blocking=True, blocking_timeout=10)
        with lock:
            yield lock
    
    @contextmanager
    def lock_transfer(self, transfer_id: str, ttl: int = 60) -> Generator[RedisLock, None, None]:
        """
        Lock a transfer operation.
        
        Usage:
            with lock_manager.lock_transfer("transfer-456"):
                # Process transfer
                pass
        """
        lock = RedisLock(self.redis, f"transfer:{transfer_id}", ttl=ttl, blocking=True, blocking_timeout=30)
        with lock:
            yield lock
    
    @contextmanager
    def lock_user_operation(self, user_id: str, operation: str, ttl: int = 10) -> Generator[RedisLock, None, None]:
        """
        Lock a user operation to prevent concurrent modifications.
        
        Usage:
            with lock_manager.lock_user_operation("user-789", "update_profile"):
                # Update user profile
                pass
        """
        lock = RedisLock(self.redis, f"user:{user_id}:{operation}", ttl=ttl, blocking=True, blocking_timeout=5)
        with lock:
            yield lock
    
    def try_lock(self, resource: str, ttl: int = 30) -> Optional[RedisLock]:
        """
        Try to acquire lock without blocking.
        
        Returns:
            RedisLock instance if acquired, None otherwise
        
        Usage:
            lock = lock_manager.try_lock("my_resource")
            if lock:
                try:
                    # Critical section
                    pass
                finally:
                    lock.release()
        """
        lock = RedisLock(self.redis, resource, ttl=ttl, blocking=False)
        if lock.acquire():
            return lock
        return None


class AsyncLockManager:
    """Async version of LockManager."""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    @asynccontextmanager
    async def lock_document(self, document_id: str, ttl: int = 30) -> AsyncGenerator[AsyncRedisLock, None]:
        """Async lock document."""
        lock = AsyncRedisLock(self.redis, f"document:{document_id}", ttl=ttl, blocking=True, blocking_timeout=10)
        async with lock:
            yield lock
    
    @asynccontextmanager
    async def lock_transfer(self, transfer_id: str, ttl: int = 60) -> AsyncGenerator[AsyncRedisLock, None]:
        """Async lock transfer."""
        lock = AsyncRedisLock(self.redis, f"transfer:{transfer_id}", ttl=ttl, blocking=True, blocking_timeout=30)
        async with lock:
            yield lock
    
    @asynccontextmanager
    async def lock_user_operation(self, user_id: str, operation: str, ttl: int = 10) -> AsyncGenerator[AsyncRedisLock, None]:
        """Async lock user operation."""
        lock = AsyncRedisLock(self.redis, f"user:{user_id}:{operation}", ttl=ttl, blocking=True, blocking_timeout=5)
        async with lock:
            yield lock
    
    async def try_lock(self, resource: str, ttl: int = 30) -> Optional[AsyncRedisLock]:
        """Try to acquire lock without blocking (async)."""
        lock = AsyncRedisLock(self.redis, resource, ttl=ttl, blocking=False)
        if await lock.acquire():
            return lock
        return None

