"""
Advanced Rate Limiter with Per-User, Sliding Window, and Tiered Limits
Enhanced version with user-based limits, quotas, and analytics
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limit tiers for different user types."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class TierConfig:
    """Configuration for a rate limit tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int  # Burst allowance
    concurrent_requests: int  # Max concurrent requests


class RateLimiterConfigAdvanced:
    """Advanced rate limiter configuration with tiers."""
    
    # Tier configurations
    TIERS = {
        RateLimitTier.FREE: TierConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_size=10,
            concurrent_requests=5
        ),
        RateLimitTier.BASIC: TierConfig(
            requests_per_minute=120,
            requests_per_hour=5000,
            requests_per_day=50000,
            burst_size=20,
            concurrent_requests=10
        ),
        RateLimitTier.PREMIUM: TierConfig(
            requests_per_minute=300,
            requests_per_hour=15000,
            requests_per_day=200000,
            burst_size=50,
            concurrent_requests=25
        ),
        RateLimitTier.ENTERPRISE: TierConfig(
            requests_per_minute=1000,
            requests_per_hour=50000,
            requests_per_day=1000000,
            burst_size=100,
            concurrent_requests=50
        )
    }
    
    # Ban configuration
    BAN_THRESHOLD = 10  # Violations before ban
    BAN_DURATION = 300  # 5 minutes
    VIOLATION_WINDOW = 600  # Track violations in 10 minutes
    
    # Allowlist (bypass rate limiting)
    ALLOWLIST_IPS = ["127.0.0.1", "::1"]
    ALLOWLIST_USERS = []  # User IDs that bypass limits
    
    # Exempt routes
    EXEMPT_ROUTES = ["/health", "/ready", "/docs", "/openapi.json"]


class AdvancedRateLimiterV2:
    """
    Advanced rate limiter with:
    - Per-user rate limiting (not just per-IP)
    - Tiered limits (free, basic, premium, enterprise)
    - Multiple time windows (minute, hour, day)
    - Burst allowance
    - Concurrent request limiting
    - Analytics and metrics
    - Quota management
    
    Usage:
        limiter = AdvancedRateLimiterV2(redis_client)
        
        # Check limit
        allowed, info = await limiter.check_limit(
            user_id="user-123",
            tier=RateLimitTier.PREMIUM,
            route="/api/documents"
        )
        
        if not allowed:
            raise HTTPException(429, detail=info)
    """
    
    def __init__(self, redis_client):
        """
        Initialize advanced rate limiter.
        
        Args:
            redis_client: Redis client (async)
        """
        self.redis = redis_client
        self.config = RateLimiterConfigAdvanced()
    
    async def check_limit(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        tier: RateLimitTier = RateLimitTier.FREE,
        route: str = "*",
        operation: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Check rate limit for user/IP.
        
        Args:
            user_id: User ID (preferred)
            ip_address: IP address (fallback)
            tier: Rate limit tier
            route: API route
            operation: Optional operation name
        
        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        # Determine identifier (user > IP)
        identifier = user_id if user_id else ip_address
        if not identifier:
            identifier = "anonymous"
        
        # Check allowlist
        if self._is_allowed(user_id, ip_address):
            return (True, {"status": "allowed", "reason": "allowlist"})
        
        # Check ban
        is_banned = await self._check_ban(identifier)
        if is_banned:
            return (False, {
                "status": "banned",
                "message": "Rate limit violations exceeded - temporarily banned",
                "retry_after": self.config.BAN_DURATION
            })
        
        # Get tier config
        tier_config = self.config.TIERS[tier]
        
        # Check multiple time windows
        minute_ok, minute_info = await self._check_window(
            identifier, tier_config.requests_per_minute, 60, "minute"
        )
        
        hour_ok, hour_info = await self._check_window(
            identifier, tier_config.requests_per_hour, 3600, "hour"
        )
        
        day_ok, day_info = await self._check_window(
            identifier, tier_config.requests_per_day, 86400, "day"
        )
        
        # Check concurrent requests
        concurrent_ok, concurrent_info = await self._check_concurrent(
            identifier, tier_config.concurrent_requests
        )
        
        # Aggregate results
        all_ok = minute_ok and hour_ok and day_ok and concurrent_ok
        
        info = {
            "status": "allowed" if all_ok else "rejected",
            "tier": tier.value,
            "limits": {
                "minute": minute_info,
                "hour": hour_info,
                "day": day_info,
                "concurrent": concurrent_info
            }
        }
        
        # Record violation if rejected
        if not all_ok:
            violations = await self._record_violation(identifier)
            info["violations"] = violations
            info["ban_threshold"] = self.config.BAN_THRESHOLD
        
        return (all_ok, info)
    
    async def _check_window(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        window_name: str
    ) -> Tuple[bool, Dict]:
        """
        Check rate limit for a specific time window.
        
        Uses sliding window algorithm with Redis sorted sets.
        
        Args:
            identifier: User/IP identifier
            limit: Request limit for this window
            window_seconds: Window size in seconds
            window_name: Window name (for logging)
        
        Returns:
            Tuple of (allowed, info)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        key = f"rl:{window_name}:{identifier}"
        
        try:
            # Remove old entries (outside window)
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in window
            count = await self.redis.zcard(key)
            
            # Check burst allowance
            tier_config = self.config.TIERS[RateLimitTier.FREE]  # Get from context
            burst_limit = limit + tier_config.burst_size
            
            if count >= burst_limit:
                # Hard limit exceeded (including burst)
                return (False, {
                    "current": count,
                    "limit": limit,
                    "burst_limit": burst_limit,
                    "remaining": 0,
                    "reset_at": int(current_time + window_seconds)
                })
            
            # Add current request
            await self.redis.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            await self.redis.expire(key, window_seconds)
            
            # New count
            new_count = count + 1
            allowed = new_count <= limit
            
            return (allowed, {
                "current": new_count,
                "limit": limit,
                "burst_limit": burst_limit,
                "remaining": max(0, limit - new_count),
                "reset_at": int(current_time + window_seconds),
                "burst_used": max(0, new_count - limit) if new_count > limit else 0
            })
        
        except Exception as e:
            logger.error(f"Error checking {window_name} window: {e}")
            # Allow on error
            return (True, {"error": str(e)})
    
    async def _check_concurrent(
        self,
        identifier: str,
        max_concurrent: int
    ) -> Tuple[bool, Dict]:
        """
        Check concurrent request limit.
        
        Args:
            identifier: User/IP identifier
            max_concurrent: Maximum concurrent requests
        
        Returns:
            Tuple of (allowed, info)
        """
        key = f"concurrent:{identifier}"
        
        try:
            # Get current concurrent count
            count_str = await self.redis.get(key)
            current = int(count_str) if count_str else 0
            
            if current >= max_concurrent:
                return (False, {
                    "current": current,
                    "limit": max_concurrent,
                    "remaining": 0
                })
            
            # Increment (will be decremented when request completes)
            new_count = await self.redis.incr(key)
            await self.redis.expire(key, 30)  # Safety expiry
            
            return (True, {
                "current": new_count,
                "limit": max_concurrent,
                "remaining": max(0, max_concurrent - new_count)
            })
        
        except Exception as e:
            logger.error(f"Error checking concurrent limit: {e}")
            return (True, {"error": str(e)})
    
    async def release_concurrent(self, identifier: str):
        """
        Release concurrent request slot.
        
        Call this when request completes.
        
        Args:
            identifier: User/IP identifier
        """
        key = f"concurrent:{identifier}"
        
        try:
            await self.redis.decr(key)
        except Exception as e:
            logger.error(f"Error releasing concurrent slot: {e}")
    
    async def _check_ban(self, identifier: str) -> bool:
        """Check if user/IP is banned."""
        key = f"ban:{identifier}"
        
        try:
            return await self.redis.exists(key) > 0
        except:
            return False
    
    async def _record_violation(self, identifier: str) -> int:
        """
        Record rate limit violation.
        
        Returns:
            Number of violations in window
        """
        key = f"violations:{identifier}"
        current_time = time.time()
        
        try:
            # Add violation
            await self.redis.zadd(key, {str(current_time): current_time})
            
            # Remove old violations
            cutoff = current_time - self.config.VIOLATION_WINDOW
            await self.redis.zremrangebyscore(key, 0, cutoff)
            
            # Set expiry
            await self.redis.expire(key, self.config.VIOLATION_WINDOW)
            
            # Count violations
            count = await self.redis.zcard(key)
            
            # Apply ban if threshold exceeded
            if count >= self.config.BAN_THRESHOLD:
                await self._apply_ban(identifier)
            
            return count
        
        except Exception as e:
            logger.error(f"Error recording violation: {e}")
            return 0
    
    async def _apply_ban(self, identifier: str):
        """Apply ban to user/IP."""
        key = f"ban:{identifier}"
        
        try:
            await self.redis.setex(key, self.config.BAN_DURATION, "1")
            logger.warning(f"🚫 BANNED: {identifier} for {self.config.BAN_DURATION}s")
        except Exception as e:
            logger.error(f"Error applying ban: {e}")
    
    def _is_allowed(self, user_id: Optional[str], ip_address: Optional[str]) -> bool:
        """Check if user/IP is in allowlist."""
        if user_id and user_id in self.config.ALLOWLIST_USERS:
            return True
        
        if ip_address and ip_address in self.config.ALLOWLIST_IPS:
            return True
        
        return False
    
    async def get_quota_usage(self, user_id: str, tier: RateLimitTier) -> Dict:
        """
        Get quota usage for user.
        
        Args:
            user_id: User ID
            tier: User's tier
        
        Returns:
            Quota usage info
        """
        tier_config = self.config.TIERS[tier]
        current_time = time.time()
        
        usage = {}
        
        for window_name, window_seconds, limit in [
            ("minute", 60, tier_config.requests_per_minute),
            ("hour", 3600, tier_config.requests_per_hour),
            ("day", 86400, tier_config.requests_per_day)
        ]:
            key = f"rl:{window_name}:{user_id}"
            
            try:
                # Count requests in window
                window_start = current_time - window_seconds
                await self.redis.zremrangebyscore(key, 0, window_start)
                count = await self.redis.zcard(key)
                
                usage[window_name] = {
                    "used": count,
                    "limit": limit,
                    "remaining": max(0, limit - count),
                    "percentage": (count / limit * 100) if limit > 0 else 0
                }
            except:
                usage[window_name] = {"error": "unavailable"}
        
        return {
            "user_id": user_id,
            "tier": tier.value,
            "usage": usage,
            "timestamp": current_time
        }
    
    async def reset_user_limits(self, user_id: str):
        """
        Reset all rate limits for a user.
        
        Admin function for manual overrides.
        
        Args:
            user_id: User ID to reset
        """
        try:
            # Find and delete all keys for user
            patterns = [
                f"rl:*:{user_id}",
                f"violations:{user_id}",
                f"ban:{user_id}",
                f"concurrent:{user_id}"
            ]
            
            for pattern in patterns:
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
            
            logger.info(f"✅ Rate limits reset for user: {user_id}")
        
        except Exception as e:
            logger.error(f"Error resetting user limits: {e}")
    
    async def get_analytics(self, window_minutes: int = 60) -> Dict:
        """
        Get rate limiting analytics.
        
        Args:
            window_minutes: Analysis window in minutes
        
        Returns:
            Analytics data
        """
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        analytics = {
            "window_minutes": window_minutes,
            "timestamp": current_time,
            "stats": {}
        }
        
        try:
            # Count violations
            violation_keys = await self.redis.keys("violations:*")
            total_violations = 0
            
            for key in violation_keys:
                count = await self.redis.zcount(key, window_start, current_time)
                total_violations += count
            
            # Count bans
            ban_keys = await self.redis.keys("ban:*")
            active_bans = len(ban_keys)
            
            # Get top violators
            top_violators = []
            for key in violation_keys[:10]:  # Top 10
                identifier = key.decode().split(":")[1]
                count = await self.redis.zcard(key)
                top_violators.append({
                    "identifier": identifier,
                    "violations": count
                })
            
            analytics["stats"] = {
                "total_violations": total_violations,
                "active_bans": active_bans,
                "top_violators": sorted(top_violators, key=lambda x: x["violations"], reverse=True)
            }
        
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            analytics["stats"] = {"error": str(e)}
        
        return analytics


# FastAPI endpoint examples
"""
from fastapi import APIRouter, Depends, HTTPException
from carpeta_common.advanced_rate_limiter import AdvancedRateLimiterV2, RateLimitTier

router = APIRouter()
limiter = AdvancedRateLimiterV2(redis_client)

@router.get("/documents")
async def list_documents(current_user: dict):
    # Check rate limit
    user_tier = RateLimitTier[current_user.get("tier", "FREE").upper()]
    
    allowed, info = await limiter.check_limit(
        user_id=current_user["id"],
        tier=user_tier,
        route="/api/documents"
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=info,
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(info["limits"]["minute"]["limit"]),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    # Process request
    return {"documents": [...]}

@router.get("/users/{user_id}/quota")
async def get_user_quota(user_id: str, current_user: dict):
    # Get quota usage
    tier = RateLimitTier[current_user.get("tier", "FREE").upper()]
    usage = await limiter.get_quota_usage(user_id, tier)
    return usage

@router.post("/admin/rate-limit/reset/{user_id}")
async def reset_rate_limit(user_id: str, current_user: dict):
    # Admin only
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(403, detail="Admin only")
    
    await limiter.reset_user_limits(user_id)
    return {"message": f"Rate limits reset for {user_id}"}

@router.get("/admin/rate-limit/analytics")
async def rate_limit_analytics(current_user: dict):
    # Admin only
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(403, detail="Admin only")
    
    analytics = await limiter.get_analytics(window_minutes=60)
    return analytics
"""

