"""Advanced rate limiter with role-based limits, sliding window, and ban system."""

import asyncio
import logging
import time
from typing import Optional, Dict, List
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiterConfig:
    """Rate limiter configuration."""
    
    # Rate limits by role (requests per minute)
    LIMITS = {
        "ciudadano": 60,
        "operador": 200,
        "mintic_client": 400,
        "transfer": 400,
        "default": 60  # Default for unauthenticated
    }
    
    # Ban configuration
    BAN_THRESHOLD = 5  # Number of violations before ban
    BAN_DURATION = 120  # Ban duration in seconds
    VIOLATION_WINDOW = 600  # Track violations in last 10 minutes
    
    # Sliding window
    WINDOW_SIZE = 60  # 60 seconds
    
    # Hub MinTIC allowlist (IPs that bypass rate limiting)
    HUB_ALLOWLIST = [
        "34.94.123.45",  # MinTIC Hub IP (example)
        "127.0.0.1",  # Localhost
        "::1",  # IPv6 localhost
    ]
    
    # Routes that bypass rate limiting
    EXEMPT_ROUTES = [
        "/health",
        "/docs",
        "/openapi.json",
        "/ops/ratelimit/status"
    ]


class AdvancedRateLimiter:
    """Advanced rate limiter with Redis sliding window and ban system."""
    
    def __init__(self, redis_client=None):
        """Initialize rate limiter.
        
        Args:
            redis_client: Redis client (optional, will try to import from common)
        """
        self.redis_client = redis_client
        self.config = RateLimiterConfig()
        
        # Try to import Redis from common
        if not self.redis_client:
            try:
                from carpeta_common.redis_client import get_redis_client
                self.redis_client = get_redis_client()
                logger.info("✅ Redis client loaded for rate limiting")
            except Exception as e:
                logger.warning(f"⚠️  Redis not available: {e}. Rate limiting disabled.")
                self.redis_client = None
        
        # Metrics
        self.service_metrics = None
        try:
            from opentelemetry import metrics
            meter = metrics.get_meter("gateway")
            
            self.rate_limit_requests = meter.create_counter(
                name="rate_limit.requests",
                description="Total rate limit checks",
                unit="1"
            )
            
            self.rate_limit_allowed = meter.create_counter(
                name="rate_limit.allowed",
                description="Allowed requests",
                unit="1"
            )
            
            self.rate_limit_rejected = meter.create_counter(
                name="rate_limit.rejected",
                description="Rejected requests",
                unit="1"
            )
            
            self.rate_limit_banned = meter.create_counter(
                name="rate_limit.banned",
                description="Banned IPs",
                unit="1"
            )
            
            logger.info("✅ OpenTelemetry metrics configured for rate limiter")
        except Exception as e:
            logger.warning(f"⚠️  OpenTelemetry not available: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_role(self, request: Request) -> str:
        """Extract role from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            User role
        """
        # Check JWT claims (from auth middleware)
        user_role = request.headers.get("X-User-Role")
        if user_role:
            return user_role.lower()
        
        # Check service name for internal calls
        service_name = request.headers.get("X-Service-Name")
        if service_name:
            if "mintic" in service_name.lower():
                return "mintic_client"
            if "transfer" in service_name.lower():
                return "transfer"
        
        # Default role
        return "default"
    
    def _is_exempt(self, request: Request, client_ip: str) -> bool:
        """Check if request is exempt from rate limiting.
        
        Args:
            request: FastAPI request
            client_ip: Client IP address
            
        Returns:
            True if exempt
        """
        # Check allowlist
        if client_ip in self.config.HUB_ALLOWLIST:
            logger.debug(f"IP {client_ip} is in allowlist (Hub MinTIC)")
            return True
        
        # Check exempt routes
        path = request.url.path
        for exempt_route in self.config.EXEMPT_ROUTES:
            if path.startswith(exempt_route):
                return True
        
        return False
    
    async def _check_ban(self, client_ip: str) -> bool:
        """Check if IP is banned.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if banned
        """
        if not self.redis_client:
            return False
        
        ban_key = f"ban:{client_ip}"
        
        try:
            # Check if ban key exists
            banned = await self.redis_client.exists(ban_key)
            return bool(banned)
        except Exception as e:
            logger.error(f"Error checking ban status: {e}")
            return False
    
    async def _record_violation(self, client_ip: str) -> int:
        """Record a rate limit violation.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Number of violations in window
        """
        if not self.redis_client:
            return 0
        
        violation_key = f"violations:{client_ip}"
        current_time = int(time.time())
        
        try:
            # Add violation with score = timestamp
            await self.redis_client.zadd(violation_key, {str(current_time): current_time})
            
            # Remove old violations (outside 10-minute window)
            cutoff = current_time - self.config.VIOLATION_WINDOW
            await self.redis_client.zremrangebyscore(violation_key, 0, cutoff)
            
            # Set expiry
            await self.redis_client.expire(violation_key, self.config.VIOLATION_WINDOW)
            
            # Count violations
            count = await self.redis_client.zcard(violation_key)
            
            # Ban if threshold exceeded
            if count >= self.config.BAN_THRESHOLD:
                await self._apply_ban(client_ip)
            
            return count
            
        except Exception as e:
            logger.error(f"Error recording violation: {e}")
            return 0
    
    async def _apply_ban(self, client_ip: str):
        """Apply ban to IP.
        
        Args:
            client_ip: Client IP address
        """
        if not self.redis_client:
            return
        
        ban_key = f"ban:{client_ip}"
        
        try:
            await self.redis_client.setex(ban_key, self.config.BAN_DURATION, "1")
            
            # Metrics
            if hasattr(self, 'rate_limit_banned'):
                self.rate_limit_banned.add(1, {"client_ip": client_ip})
            
            logger.warning(
                f"🚫 IP {client_ip} BANNED for {self.config.BAN_DURATION}s "
                f"(threshold: {self.config.BAN_THRESHOLD} violations)"
            )
        except Exception as e:
            logger.error(f"Error applying ban: {e}")
    
    async def _check_rate_limit(
        self,
        client_ip: str,
        route: str,
        role: str
    ) -> tuple[bool, int, int]:
        """Check rate limit using sliding window.
        
        Args:
            client_ip: Client IP address
            route: Request route
            role: User role
            
        Returns:
            Tuple of (allowed, current_count, limit)
        """
        if not self.redis_client:
            return (True, 0, 0)
        
        # Get limit for role
        limit = self.config.LIMITS.get(role, self.config.LIMITS["default"])
        
        # Current time and bucket
        current_time = time.time()
        current_bucket = int(current_time / self.config.WINDOW_SIZE)
        
        # Redis key with sliding window buckets
        # Format: rl:{route}:{role}:{ip}:{bucket}
        key = f"rl:{route}:{role}:{client_ip}:{current_bucket}"
        
        try:
            # Increment counter
            count = await self.redis_client.incr(key)
            
            # Set expiry on first increment
            if count == 1:
                await self.redis_client.expire(key, self.config.WINDOW_SIZE)
            
            # Check if limit exceeded
            allowed = count <= limit
            
            return (allowed, count, limit)
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Allow on error
            return (True, 0, limit)
    
    async def check_request(self, request: Request) -> Optional[Dict]:
        """Check if request should be rate limited.
        
        Args:
            request: FastAPI request
            
        Returns:
            None if allowed, error dict if rejected
        """
        # Get client info
        client_ip = self._get_client_ip(request)
        role = self._get_role(request)
        route = request.url.path
        
        # Metrics
        if hasattr(self, 'rate_limit_requests'):
            self.rate_limit_requests.add(1, {
                "role": role,
                "route": route[:50]  # Truncate long routes
            })
        
        # Check if exempt
        if self._is_exempt(request, client_ip):
            return None
        
        # Check if banned
        is_banned = await self._check_ban(client_ip)
        if is_banned:
            logger.warning(f"🚫 Banned IP attempted request: {client_ip}")
            
            if hasattr(self, 'rate_limit_rejected'):
                self.rate_limit_rejected.add(1, {
                    "reason": "banned",
                    "role": role,
                    "client_ip": client_ip
                })
            
            return {
                "error": "IP banned",
                "message": f"Your IP {client_ip} is temporarily banned due to excessive rate limit violations",
                "retry_after": self.config.BAN_DURATION
            }
        
        # Check rate limit
        allowed, current_count, limit = await self._check_rate_limit(
            client_ip, route, role
        )
        
        if allowed:
            # Metrics
            if hasattr(self, 'rate_limit_allowed'):
                self.rate_limit_allowed.add(1, {
                    "role": role,
                    "route": route[:50]
                })
            
            return None
        else:
            # Record violation
            violations = await self._record_violation(client_ip)
            
            # Metrics
            if hasattr(self, 'rate_limit_rejected'):
                self.rate_limit_rejected.add(1, {
                    "reason": "rate_limit",
                    "role": role,
                    "client_ip": client_ip
                })
            
            logger.warning(
                f"⚠️  Rate limit exceeded: {client_ip} ({role}) "
                f"route={route} count={current_count}/{limit} "
                f"violations={violations}/{self.config.BAN_THRESHOLD}"
            )
            
            return {
                "error": "Rate limit exceeded",
                "message": f"Rate limit exceeded for role '{role}': {current_count}/{limit} requests per minute",
                "limit": limit,
                "current": current_count,
                "retry_after": 60,
                "violations": violations,
                "ban_threshold": self.config.BAN_THRESHOLD
            }
    
    async def get_status(self, client_ip: Optional[str] = None) -> Dict:
        """Get rate limiter status.
        
        Args:
            client_ip: Optional IP to get specific status
            
        Returns:
            Status dict
        """
        status = {
            "redis_available": self.redis_client is not None,
            "config": {
                "limits": self.config.LIMITS,
                "ban_threshold": self.config.BAN_THRESHOLD,
                "ban_duration": self.config.BAN_DURATION,
                "window_size": self.config.WINDOW_SIZE,
                "allowlist": self.config.HUB_ALLOWLIST
            }
        }
        
        # Get IP-specific status
        if client_ip and self.redis_client:
            try:
                # Check ban
                is_banned = await self._check_ban(client_ip)
                
                # Get violations
                violation_key = f"violations:{client_ip}"
                violation_count = await self.redis_client.zcard(violation_key)
                
                # Get current counters for each role
                current_time = time.time()
                current_bucket = int(current_time / self.config.WINDOW_SIZE)
                
                counters = {}
                for role in self.config.LIMITS.keys():
                    key_pattern = f"rl:*:{role}:{client_ip}:{current_bucket}"
                    keys = await self.redis_client.keys(key_pattern)
                    
                    role_count = 0
                    for key in keys:
                        count = await self.redis_client.get(key)
                        if count:
                            role_count += int(count)
                    
                    counters[role] = {
                        "current": role_count,
                        "limit": self.config.LIMITS[role]
                    }
                
                status["ip_status"] = {
                    "ip": client_ip,
                    "banned": is_banned,
                    "violations": violation_count,
                    "counters": counters
                }
                
            except Exception as e:
                logger.error(f"Error getting IP status: {e}")
                status["ip_status"] = {"error": str(e)}
        
        return status


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, rate_limiter: AdvancedRateLimiter):
        """Initialize middleware.
        
        Args:
            app: FastAPI app
            rate_limiter: Rate limiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter.
        
        Args:
            request: FastAPI request
            call_next: Next middleware
            
        Returns:
            Response
        """
        # Check rate limit
        error = await self.rate_limiter.check_request(request)
        
        if error:
            # Return 429 Too Many Requests
            from fastapi.responses import JSONResponse
            
            return JSONResponse(
                status_code=429,
                content=error,
                headers={
                    "Retry-After": str(error.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(error.get("limit", 0)),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Continue processing
        response = await call_next(request)
        
        return response

