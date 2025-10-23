"""Redis client for MinTIC Client Service."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for MinTIC Client Service."""

    def __init__(self, settings: Settings):
        """Initialize Redis client."""
        self.settings = settings
        self.client: Optional[Redis] = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build Redis connection string for Azure Cache for Redis."""
        if self.settings.redis_ssl:
            protocol = "rediss"
        else:
            protocol = "redis"
        
        # Azure Cache for Redis format: rediss://:password@host:port/db
        if self.settings.redis_password:
            return f"{protocol}://:{self.settings.redis_password}@{self.settings.redis_host}:{self.settings.redis_port}/0"
        else:
            return f"{protocol}://{self.settings.redis_host}:{self.settings.redis_port}/0"

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.from_url(
                self._connection_string,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Redis")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        if not self.client:
            logger.warning("Redis client not connected")
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Redis key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        if not self.client:
            logger.warning("Redis client not connected")
            return None
        
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Failed to get Redis key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.client:
            logger.warning("Redis client not connected")
            return False
        
        try:
            result = await self.client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete Redis key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.client:
            logger.warning("Redis client not connected")
            return False
        
        try:
            result = await self.client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to check Redis key {key}: {e}")
            return False

    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Set a key-value pair with TTL in Redis."""
        return await self.set(key, value, ttl)

    async def ttl(self, key: str) -> int:
        """Get TTL for a key in Redis."""
        if not self.client:
            logger.warning("Redis client not connected")
            return -1
        
        try:
            return await self.client.ttl(key)
            
        except Exception as e:
            logger.error(f"Failed to get TTL for Redis key {key}: {e}")
            return -1

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching a pattern."""
        if not self.client:
            logger.warning("Redis client not connected")
            return []
        
        try:
            return await self.client.keys(pattern)
            
        except Exception as e:
            logger.error(f"Failed to get Redis keys with pattern {pattern}: {e}")
            return []

    async def flushdb(self) -> bool:
        """Flush current database."""
        if not self.client:
            logger.warning("Redis client not connected")
            return False
        
        try:
            await self.client.flushdb()
            return True
            
        except Exception as e:
            logger.error(f"Failed to flush Redis database: {e}")
            return False

    async def info(self) -> dict:
        """Get Redis server information."""
        if not self.client:
            logger.warning("Redis client not connected")
            return {}
        
        try:
            info = await self.client.info()
            return info
            
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}

    async def ping(self) -> bool:
        """Ping Redis server."""
        if not self.client:
            return False
        
        try:
            result = await self.client.ping()
            return result is True
            
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
