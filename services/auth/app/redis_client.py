"""Async Redis client utilities for the Auth service."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import redis.asyncio as redis

from app.config import get_config

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_lock = asyncio.Lock()


def _build_redis_url() -> str:
    """Build Redis connection URL based on configuration."""
    config = get_config()
    scheme = "rediss" if config.redis_ssl else "redis"

    auth_part = ""
    if config.redis_password:
        auth_part = f":{config.redis_password}@"

    return f"{scheme}://{auth_part}{config.redis_host}:{config.redis_port}/{config.redis_db}"


def _redact_url(url: str) -> str:
    """Redact credentials in Redis URL for logging."""
    if "@" not in url or "://" not in url:
        return url
    prefix, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    creds, host_part = rest.split("@", 1)
    redacted = "***" if creds else ""
    return f"{prefix}://{redacted}@{host_part}"


async def get_redis_client() -> redis.Redis:
    """Get a singleton Redis async client."""
    config = get_config()
    if not config.redis_enabled:
        raise RuntimeError("Redis cache is disabled by configuration")

    global _redis_client

    if _redis_client is None:
        async with _lock:
            if _redis_client is None:
                url = _build_redis_url()
                timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", "3.0"))
                logger.info("Connecting to Redis at %s", _redact_url(url))

                client = redis.from_url(
                    url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=timeout,
                    socket_connect_timeout=timeout,
                    health_check_interval=30,
                )

                try:
                    await client.ping()
                    logger.info("✅ Redis connection established")
                    _redis_client = client
                except Exception:
                    logger.exception("❌ Unable to connect to Redis")
                    await client.close()
                    raise

    if _redis_client is None:
        raise RuntimeError("Redis client is not available")

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client (for shutdown/tests)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


