"""Azure Redis Cache integration for transfer service."""

import logging
import json
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis libraries not available. Running in local mode.")

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AzureRedisService:
    """Azure Redis Cache service with fallback to local memory."""
    
    def __init__(self):
        self.client = None
        self.is_available = False
        self._local_cache = {}  # Fallback local cache
        
        if REDIS_AVAILABLE and settings.redis_host and settings.redis_password:
            try:
                self._initialize_client()
                self.is_available = True
                logger.info("Azure Redis client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Redis: {e}")
                self.is_available = False
        else:
            logger.info("Azure Redis not configured, using local cache fallback")
    
    def _initialize_client(self):
        """Initialize Azure Redis client."""
        self.client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    async def set_transfer_cache(
        self,
        transfer_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache transfer data in Redis."""
        try:
            if not self.is_available:
                return await self._local_set(transfer_id, data, ttl_seconds)
            
            cache_key = f"transfer:{transfer_id}"
            await self.client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(data)
            )
            
            logger.info(f"Transfer {transfer_id} cached in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache transfer {transfer_id}: {e}")
            return await self._local_set(transfer_id, data, ttl_seconds)
    
    async def _local_set(
        self,
        transfer_id: str,
        data: Dict[str, Any],
        ttl_seconds: int
    ) -> bool:
        """Local cache fallback."""
        cache_key = f"transfer:{transfer_id}"
        self._local_cache[cache_key] = {
            "data": data,
            "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds)
        }
        
        logger.info(f"Transfer {transfer_id} cached locally")
        return True
    
    async def get_transfer_cache(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get transfer data from cache."""
        try:
            if not self.is_available:
                return await self._local_get(transfer_id)
            
            cache_key = f"transfer:{transfer_id}"
            cached_data = await self.client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transfer cache {transfer_id}: {e}")
            return await self._local_get(transfer_id)
    
    async def _local_get(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Local cache get fallback."""
        cache_key = f"transfer:{transfer_id}"
        
        if cache_key in self._local_cache:
            cache_entry = self._local_cache[cache_key]
            if datetime.utcnow() < cache_entry["expires"]:
                return cache_entry["data"]
            else:
                # Expired, remove from cache
                del self._local_cache[cache_key]
        
        return None
    
    async def set_idempotency_key(
        self,
        idempotency_key: str,
        ttl_seconds: int = 3600  # 1 hour
    ) -> bool:
        """Set idempotency key using Redis SETNX for distributed locking."""
        try:
            if not self.is_available:
                return await self._local_set_idempotency_nx(idempotency_key, ttl_seconds)
            
            cache_key = f"idempotency:{idempotency_key}"
            # Use SETNX (SET if Not eXists) for atomic idempotency
            was_set = await self.client.setnx(cache_key, "processing")
            
            if was_set:
                # Set expiration only if we successfully acquired the key
                await self.client.expire(cache_key, ttl_seconds)
                logger.info(f"Idempotency key {idempotency_key} acquired via Redis SETNX")
                return True
            else:
                logger.warning(f"Idempotency key {idempotency_key} already exists in Redis")
                return False
            
        except Exception as e:
            logger.error(f"Failed to set idempotency key {idempotency_key}: {e}")
            return await self._local_set_idempotency_nx(idempotency_key, ttl_seconds)
    
    async def _local_set_idempotency_nx(
        self,
        idempotency_key: str,
        ttl_seconds: int
    ) -> bool:
        """Local idempotency cache fallback with SETNX behavior."""
        cache_key = f"idempotency:{idempotency_key}"
        
        # Check if key already exists (SETNX behavior)
        if cache_key in self._local_cache:
            cache_entry = self._local_cache[cache_key]
            if datetime.utcnow() < cache_entry["expires"]:
                logger.warning(f"Idempotency key {idempotency_key} already exists locally")
                return False
            else:
                # Expired, remove it
                del self._local_cache[cache_key]
        
        # Set the key (SETNX behavior)
        self._local_cache[cache_key] = {
            "data": "processing",
            "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds)
        }
        
        logger.info(f"Idempotency key {idempotency_key} acquired locally")
        return True
    
    async def get_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Check if idempotency key exists."""
        try:
            if not self.is_available:
                return await self._local_get_idempotency(idempotency_key)
            
            cache_key = f"idempotency:{idempotency_key}"
            cached_data = await self.client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get idempotency key {idempotency_key}: {e}")
            return await self._local_get_idempotency(idempotency_key)
    
    async def _local_get_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Local idempotency cache get fallback."""
        cache_key = f"idempotency:{idempotency_key}"
        
        if cache_key in self._local_cache:
            cache_entry = self._local_cache[cache_key]
            if datetime.utcnow() < cache_entry["expires"]:
                return cache_entry["data"]
            else:
                # Expired, remove from cache
                del self._local_cache[cache_key]
        
        return None
    
    async def delete_idempotency_key(self, idempotency_key: str) -> bool:
        """Delete idempotency key after processing."""
        try:
            if not self.is_available:
                return await self._local_delete_idempotency(idempotency_key)
            
            cache_key = f"idempotency:{idempotency_key}"
            await self.client.delete(cache_key)
            
            logger.info(f"Idempotency key {idempotency_key} deleted from Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete idempotency key {idempotency_key}: {e}")
            return await self._local_delete_idempotency(idempotency_key)
    
    async def _local_delete_idempotency(self, idempotency_key: str) -> bool:
        """Local idempotency delete fallback."""
        cache_key = f"idempotency:{idempotency_key}"
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
            logger.info(f"Idempotency key {idempotency_key} deleted from local cache")
            return True
        return False

    async def delete_transfer_cache(self, transfer_id: str) -> bool:
        """Delete transfer from cache."""
        try:
            if not self.is_available:
                return await self._local_delete(transfer_id)
            
            cache_key = f"transfer:{transfer_id}"
            await self.client.delete(cache_key)
            
            logger.info(f"Transfer {transfer_id} deleted from Redis cache")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete transfer cache {transfer_id}: {e}")
            return await self._local_delete(transfer_id)
    
    async def _local_delete(self, transfer_id: str) -> bool:
        """Local cache delete fallback."""
        cache_key = f"transfer:{transfer_id}"
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
            logger.info(f"Transfer {transfer_id} deleted from local cache")
            return True
        
        return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            if not self.is_available:
                return {
                    "status": "local_fallback",
                    "message": "Using local cache fallback",
                    "local_cache_size": len(self._local_cache)
                }
            
            # Test Redis connection
            await self.client.ping()
            
            # Get Redis info
            info = await self.client.info()
            
            return {
                "status": "healthy",
                "message": "Azure Redis is available",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Redis health check failed: {e}",
                "fallback": "local_cache"
            }


# Global instance
azure_redis = AzureRedisService()
