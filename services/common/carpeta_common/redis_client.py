"""Redis async client and utilities for distributed operations.

Supports Azure Cache for Redis (TLS on 6380) and local Redis for development.
"""

import json
import logging
import os
import uuid
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as redis

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_url() -> str:
    """Build Redis URL from environment variables.
    
    Azure Cache for Redis:
        - REDIS_HOST: <name>.redis.cache.windows.net
        - REDIS_PORT: 6380
        - REDIS_SSL: true
        - REDIS_PASSWORD: <primary-key>
    
    Local development:
        - REDIS_HOST: localhost
        - REDIS_PORT: 6379
        - REDIS_SSL: false (no TLS)
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", "")
    ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
    db = int(os.getenv("REDIS_DB", "0"))
    
    # Build URL
    if ssl:
        scheme = "rediss"  # Redis with TLS
    else:
        scheme = "redis"
    
    if password:
        url = f"{scheme}://:{password}@{host}:{port}/{db}"
    else:
        url = f"{scheme}://{host}:{port}/{db}"
    
    logger.info(f"Redis URL: {scheme}://{host}:{port}/{db} (SSL={ssl})")
    return url


async def get_redis_client() -> redis.Redis:
    """Get or create Redis async client."""
    global _redis_client
    
    if _redis_client is None:
        url = get_redis_url()
        socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", "2"))
        
        _redis_client = redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            health_check_interval=30,
        )
        
        # Test connection
        try:
            await _redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


# =============================================================================
# JSON utilities
# =============================================================================

async def get_json(key: str) -> Optional[dict]:
    """Get JSON object from Redis.
    
    Args:
        key: Redis key
        
    Returns:
        Deserialized JSON object or None if not found
    """
    client = await get_redis_client()
    value = await client.get(key)
    
    if value is None:
        return None
    
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON for key {key}: {e}")
        return None


async def set_json(key: str, obj: Any, ttl: Optional[int] = None) -> bool:
    """Set JSON object in Redis with optional TTL.
    
    Args:
        key: Redis key
        obj: Object to serialize as JSON
        ttl: Time-to-live in seconds (optional)
        
    Returns:
        True if successful
    """
    client = await get_redis_client()
    value = json.dumps(obj)
    
    if ttl:
        return await client.setex(key, ttl, value)
    else:
        return await client.set(key, value)


async def setnx(key: str, value: str, ttl: Optional[int] = None) -> bool:
    """Set key only if it does not exist (SET if Not eXists).
    
    Args:
        key: Redis key
        value: Value to set
        ttl: Time-to-live in seconds (optional)
        
    Returns:
        True if key was set, False if key already exists
    """
    client = await get_redis_client()
    
    if ttl:
        # SET key value EX ttl NX
        result = await client.set(key, value, ex=ttl, nx=True)
    else:
        result = await client.setnx(key, value)
    
    return bool(result)


# =============================================================================
# Distributed locks
# =============================================================================

async def acquire_lock(key: str, ttl: int = 10) -> Optional[str]:
    """Acquire distributed lock with auto-expiration.
    
    Args:
        key: Lock key (e.g., "lock:operation:resource_id")
        ttl: Lock TTL in seconds (default: 10s)
        
    Returns:
        Lock token (UUID) if acquired, None if lock already held
    """
    token = str(uuid.uuid4())
    
    if await setnx(key, token, ttl):
        logger.debug(f"🔒 Lock acquired: {key} (token={token[:8]}...)")
        return token
    
    logger.debug(f"⏳ Lock busy: {key}")
    return None


async def release_lock(key: str, token: str) -> bool:
    """Release distributed lock with token verification.
    
    Args:
        key: Lock key
        token: Lock token from acquire_lock
        
    Returns:
        True if lock was released, False if lock owned by another token
    """
    client = await get_redis_client()
    
    # Lua script for atomic compare-and-delete
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    
    result = await client.eval(lua_script, 1, key, token)
    
    if result:
        logger.debug(f"🔓 Lock released: {key}")
        return True
    
    logger.warning(f"⚠️ Lock release failed (wrong token): {key}")
    return False


async def with_lock(
    lock_key: str,
    ttl: int,
    fn: Callable[[], T],
    timeout: int = 30,
    poll_interval: float = 0.1,
) -> T:
    """Execute function with distributed lock (blocking wait).
    
    Args:
        lock_key: Lock key
        ttl: Lock TTL in seconds
        fn: Async function to execute
        timeout: Max wait time for lock (seconds)
        poll_interval: Poll interval when waiting (seconds)
        
    Returns:
        Result of fn()
        
    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    import asyncio
    
    elapsed = 0.0
    token = None
    
    # Try to acquire lock with polling
    while elapsed < timeout:
        token = await acquire_lock(lock_key, ttl)
        if token:
            break
        
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    
    if not token:
        raise TimeoutError(f"Failed to acquire lock {lock_key} within {timeout}s")
    
    try:
        # Execute function
        return await fn()
    finally:
        # Always release lock
        await release_lock(lock_key, token)


# =============================================================================
# Rate limiting (sliding window)
# =============================================================================

async def check_rate_limit(
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int]:
    """Check rate limit using sliding window counter.
    
    Args:
        key: Rate limit key (e.g., "rl:api:192.168.1.1")
        limit: Max requests per window
        window: Time window in seconds
        
    Returns:
        (allowed, remaining): allowed=True if under limit, remaining count
    """
    client = await get_redis_client()
    
    # Use sorted set with timestamps as scores
    now = int(os.times()[4] * 1000)  # Current time in milliseconds
    window_start = now - (window * 1000)
    
    # Lua script for atomic rate limit check
    lua_script = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window_start = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local window_ttl = tonumber(ARGV[4])
    
    -- Remove old entries
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
    
    -- Get current count
    local current = redis.call('ZCARD', key)
    
    if current < limit then
        -- Add current request
        redis.call('ZADD', key, now, now)
        redis.call('EXPIRE', key, window_ttl)
        return {1, limit - current - 1}
    else
        return {0, 0}
    end
    """
    
    result = await client.eval(
        lua_script,
        1,
        key,
        now,
        window_start,
        limit,
        window + 10,  # TTL slightly longer than window
    )
    
    allowed = bool(result[0])
    remaining = int(result[1])
    
    return (allowed, remaining)


# =============================================================================
# Cache utilities
# =============================================================================

async def get_or_set_cache(
    key: str,
    fetch_fn: Callable[[], T],
    ttl: int,
    lock_ttl: int = 10,
) -> T:
    """Get value from cache or fetch and cache it (single-flight pattern).
    
    Prevents cache stampede by using a distributed lock so only one
    caller fetches the value while others wait.
    
    Args:
        key: Cache key
        fetch_fn: Async function to fetch value if not in cache
        ttl: Cache TTL in seconds
        lock_ttl: Lock TTL in seconds (should be < ttl)
        
    Returns:
        Cached or freshly fetched value
    """
    import asyncio
    
    # Try to get from cache
    cached = await get_json(key)
    if cached is not None:
        logger.debug(f"📦 Cache HIT: {key}")
        return cached
    
    logger.debug(f"❌ Cache MISS: {key}")
    
    # Try to acquire lock to fetch
    lock_key = f"lock:{key}"
    token = await acquire_lock(lock_key, lock_ttl)
    
    if token:
        # We got the lock, fetch and cache
        try:
            value = await fetch_fn()
            await set_json(key, value, ttl)
            logger.info(f"✅ Cache SET: {key} (TTL={ttl}s)")
            return value
        finally:
            await release_lock(lock_key, token)
    else:
        # Another process is fetching, wait and retry
        logger.debug(f"⏳ Waiting for cache fetch: {key}")
        
        for _ in range(lock_ttl * 10):  # Poll for lock_ttl seconds
            await asyncio.sleep(0.1)
            cached = await get_json(key)
            if cached is not None:
                logger.debug(f"📦 Cache HIT (after wait): {key}")
                return cached
        
        # Timeout waiting for other process, fetch ourselves
        logger.warning(f"⚠️ Cache fetch timeout, fetching: {key}")
        value = await fetch_fn()
        await set_json(key, value, ttl)
        return value

