"""Hub-specific rate limiter to protect MinTIC public hub from saturation.

CONTEXT:
- MinTIC hub is PUBLIC (shared by all operators)
- We MUST NOT saturate it with excessive requests
- Rate limit per endpoint: 10 req/min (configurable)
- If limit reached → 202 Accepted + queue for retry
- If circuit breaker OPEN → 202 Accepted + queue for retry
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from carpeta_common.redis_client import get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️  Redis not available, hub rate limiting disabled")

try:
    from opentelemetry import metrics
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class HubRateLimiter:
    """Rate limiter specifically for MinTIC hub calls.
    
    Protects the public hub from accidental saturation.
    Uses sliding window algorithm in Redis.
    """
    
    def __init__(self, requests_per_minute: int = 10, enabled: bool = True):
        """Initialize hub rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute per endpoint
            enabled: Whether rate limiting is enabled
        """
        self.requests_per_minute = requests_per_minute
        self.enabled = enabled
        self.redis_client = None
        
        if enabled and REDIS_AVAILABLE:
            try:
                self.redis_client = get_redis_client()
                logger.info(
                    f"✅ Hub rate limiter initialized: {requests_per_minute} req/min per endpoint"
                )
            except Exception as e:
                logger.warning(f"⚠️  Failed to connect to Redis: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️  Hub rate limiting disabled")
        
        # OpenTelemetry metrics
        if OTEL_AVAILABLE:
            meter = metrics.get_meter(__name__)
            self.rate_limit_exceeded = meter.create_counter(
                "hub.rate_limit.exceeded",
                description="Number of hub calls rate limited"
            )
            self.rate_limit_remaining = meter.create_up_down_counter(
                "hub.rate_limit.remaining",
                description="Remaining hub calls in current window"
            )
    
    async def check_limit(self, endpoint: str) -> tuple[bool, int]:
        """Check if hub call is allowed.
        
        Args:
            endpoint: Hub endpoint name (e.g., "registerCitizen")
            
        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        if not self.enabled or not self.redis_client:
            return True, self.requests_per_minute
        
        try:
            # Sliding window key: hub:ratelimit:{endpoint}:{current_minute}
            current_minute = int(time.time() / 60)
            key = f"hub:ratelimit:{endpoint}:{current_minute}"
            
            # Get current count
            current_count = await self.redis_client.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            
            remaining = self.requests_per_minute - current_count
            
            # Check if limit exceeded
            if current_count >= self.requests_per_minute:
                logger.warning(
                    f"⚠️  Hub rate limit EXCEEDED for {endpoint}: "
                    f"{current_count}/{self.requests_per_minute} req/min"
                )
                
                # Record metric
                if OTEL_AVAILABLE and hasattr(self, 'rate_limit_exceeded'):
                    self.rate_limit_exceeded.add(1, {"endpoint": endpoint})
                
                return False, 0
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 60)  # TTL: 60 seconds
            await pipe.execute()
            
            remaining -= 1
            
            # Record remaining metric
            if OTEL_AVAILABLE and hasattr(self, 'rate_limit_remaining'):
                self.rate_limit_remaining.add(
                    remaining,
                    {"endpoint": endpoint}
                )
            
            logger.debug(
                f"✅ Hub rate limit OK for {endpoint}: "
                f"{current_count + 1}/{self.requests_per_minute} "
                f"(remaining: {remaining})"
            )
            
            return True, remaining
            
        except Exception as e:
            logger.error(f"❌ Hub rate limit check failed: {e}")
            # On error, allow the request (fail open)
            return True, self.requests_per_minute
    
    async def get_current_usage(self, endpoint: str) -> dict:
        """Get current rate limit usage for endpoint.
        
        Args:
            endpoint: Hub endpoint name
            
        Returns:
            Dict with current, limit, remaining, reset_at
        """
        if not self.enabled or not self.redis_client:
            return {
                "enabled": False,
                "current": 0,
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute,
                "reset_at": None
            }
        
        try:
            current_minute = int(time.time() / 60)
            key = f"hub:ratelimit:{endpoint}:{current_minute}"
            
            current_count = await self.redis_client.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            
            remaining = max(0, self.requests_per_minute - current_count)
            reset_at = (current_minute + 1) * 60  # Next minute
            
            return {
                "enabled": True,
                "endpoint": endpoint,
                "current": current_count,
                "limit": self.requests_per_minute,
                "remaining": remaining,
                "reset_at": reset_at,
                "reset_in_seconds": reset_at - int(time.time())
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get hub rate limit usage: {e}")
            return {
                "enabled": True,
                "error": str(e),
                "current": 0,
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute,
                "reset_at": None
            }

