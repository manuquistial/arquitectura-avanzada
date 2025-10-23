"""Azure Redis client with error handling and caching for read models."""

import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AzureRedisClient:
    """Azure Redis client with error handling for caching read models."""
    
    def __init__(self, settings):
        self.settings = settings
        self.redis_client = None
        self.connected = False
        
        # Initialize Redis client with Azure configuration
        try:
            import redis.asyncio as redis
            
            # Azure Redis configuration
            if settings.is_azure_environment():
                # Azure Redis Cache configuration
                redis_config = {
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "password": settings.redis_password if settings.redis_password else None,
                    "ssl": settings.redis_ssl,
                    "decode_responses": True,
                    "socket_connect_timeout": 5,
                    "socket_timeout": 5,
                    "retry_on_timeout": True,
                    "health_check_interval": 30
                }
            else:
                # Local Redis configuration
                redis_config = {
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "decode_responses": True,
                    "socket_connect_timeout": 5,
                    "socket_timeout": 5,
                    "retry_on_timeout": True
                }
            
            self.redis_client = redis.Redis(**redis_config)
            logger.info("✅ Redis client initialized")
            
        except ImportError:
            logger.error("❌ redis package not installed")
            self.redis_client = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis client: {e}")
            self.redis_client = None
    
    async def connect(self) -> bool:
        """Test Redis connection."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            self.connected = True
            logger.info("✅ Redis connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                self.connected = False
                logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing Redis connection: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.connected or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis cache with TTL."""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"❌ Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Redis DELETE error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern."""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"❌ Redis DELETE pattern error for {pattern}: {e}")
            return False
    
    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)
    
    async def cache_documents_query(self, citizen_id: Optional[int], state: Optional[str], 
                                  limit: int, offset: int, result: Dict[str, Any]) -> bool:
        """Cache documents query result."""
        cache_key = self.generate_cache_key(
            "documents",
            citizen_id=citizen_id,
            state=state,
            limit=limit,
            offset=offset
        )
        
        # Cache for 5 minutes
        return await self.set(cache_key, result, ttl=300)
    
    async def get_cached_documents_query(self, citizen_id: Optional[int], state: Optional[str], 
                                       limit: int, offset: int) -> Optional[Dict[str, Any]]:
        """Get cached documents query result."""
        cache_key = self.generate_cache_key(
            "documents",
            citizen_id=citizen_id,
            state=state,
            limit=limit,
            offset=offset
        )
        
        return await self.get(cache_key)
    
    async def cache_transfers_query(self, citizen_id: Optional[int], status: Optional[str], 
                                   limit: int, offset: int, result: Dict[str, Any]) -> bool:
        """Cache transfers query result."""
        cache_key = self.generate_cache_key(
            "transfers",
            citizen_id=citizen_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Cache for 5 minutes
        return await self.set(cache_key, result, ttl=300)
    
    async def get_cached_transfers_query(self, citizen_id: Optional[int], status: Optional[str], 
                                       limit: int, offset: int) -> Optional[Dict[str, Any]]:
        """Get cached transfers query result."""
        cache_key = self.generate_cache_key(
            "transfers",
            citizen_id=citizen_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return await self.get(cache_key)
    
    async def cache_stats_query(self, citizen_id: int, result: Dict[str, Any]) -> bool:
        """Cache stats query result."""
        cache_key = self.generate_cache_key("stats", citizen_id=citizen_id)
        
        # Cache for 10 minutes
        return await self.set(cache_key, result, ttl=600)
    
    async def get_cached_stats_query(self, citizen_id: int) -> Optional[Dict[str, Any]]:
        """Get cached stats query result."""
        cache_key = self.generate_cache_key("stats", citizen_id=citizen_id)
        return await self.get(cache_key)
    
    async def invalidate_citizen_cache(self, citizen_id: int):
        """Invalidate all cache entries for a citizen."""
        try:
            # Delete documents cache
            await self.delete_pattern(f"documents:citizen_id:{citizen_id}:*")
            # Delete transfers cache
            await self.delete_pattern(f"transfers:citizen_id:{citizen_id}:*")
            # Delete stats cache
            await self.delete_pattern(f"stats:citizen_id:{citizen_id}")
            logger.info(f"✅ Invalidated cache for citizen {citizen_id}")
        except Exception as e:
            logger.error(f"❌ Error invalidating cache for citizen {citizen_id}: {e}")
    
    async def invalidate_document_cache(self, document_id: str):
        """Invalidate cache when document is updated."""
        try:
            # Delete all document-related cache entries
            await self.delete_pattern(f"documents:*")
            logger.info(f"✅ Invalidated document cache for {document_id}")
        except Exception as e:
            logger.error(f"❌ Error invalidating document cache for {document_id}: {e}")
    
    async def invalidate_transfer_cache(self, transfer_id: str):
        """Invalidate cache when transfer is updated."""
        try:
            # Delete all transfer-related cache entries
            await self.delete_pattern(f"transfers:*")
            logger.info(f"✅ Invalidated transfer cache for {transfer_id}")
        except Exception as e:
            logger.error(f"❌ Error invalidating transfer cache for {transfer_id}: {e}")


# Global Redis client instance
redis_client = None


async def get_redis_client(settings) -> Optional[AzureRedisClient]:
    """Get or create Redis client instance."""
    global redis_client
    
    if redis_client is None:
        redis_client = AzureRedisClient(settings)
        await redis_client.connect()
    
    return redis_client if redis_client.connected else None
