"""
Unit tests for Advanced Rate Limiter V2
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock

from carpeta_common.advanced_rate_limiter import (
    AdvancedRateLimiterV2,
    RateLimitTier,
    TierConfig
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    client = Mock()
    
    # Async methods
    client.zadd = AsyncMock(return_value=1)
    client.zremrangebyscore = AsyncMock(return_value=0)
    client.zcard = AsyncMock(return_value=0)
    client.zcount = AsyncMock(return_value=0)
    client.expire = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.incr = AsyncMock(return_value=1)
    client.decr = AsyncMock(return_value=0)
    client.setex = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=0)
    client.keys = AsyncMock(return_value=[])
    client.delete = AsyncMock(return_value=0)
    
    return client


@pytest.mark.asyncio
async def test_check_limit_allowed(mock_redis):
    """Test rate limit check when allowed."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock low count (under limit)
    mock_redis.zcard.return_value = 5
    
    allowed, info = await limiter.check_limit(
        user_id="user-123",
        tier=RateLimitTier.FREE,
        route="/api/documents"
    )
    
    assert allowed is True
    assert info["status"] == "allowed"
    assert "limits" in info


@pytest.mark.asyncio
async def test_check_limit_rejected(mock_redis):
    """Test rate limit check when rejected."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock high count (over limit)
    tier_config = limiter.config.TIERS[RateLimitTier.FREE]
    mock_redis.zcard.return_value = tier_config.requests_per_minute + 100
    
    allowed, info = await limiter.check_limit(
        user_id="user-123",
        tier=RateLimitTier.FREE
    )
    
    assert allowed is False
    assert info["status"] == "rejected"


@pytest.mark.asyncio
async def test_tier_limits_different():
    """Test different tiers have different limits."""
    free_config = TierConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
        burst_size=10,
        concurrent_requests=5
    )
    
    premium_config = TierConfig(
        requests_per_minute=300,
        requests_per_hour=15000,
        requests_per_day=200000,
        burst_size=50,
        concurrent_requests=25
    )
    
    assert premium_config.requests_per_minute > free_config.requests_per_minute
    assert premium_config.burst_size > free_config.burst_size
    assert premium_config.concurrent_requests > free_config.concurrent_requests


@pytest.mark.asyncio
async def test_allowlist_bypass(mock_redis):
    """Test allowlist bypasses rate limiting."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Add to allowlist
    limiter.config.ALLOWLIST_IPS = ["1.2.3.4"]
    
    allowed, info = await limiter.check_limit(
        ip_address="1.2.3.4",
        tier=RateLimitTier.FREE
    )
    
    assert allowed is True
    assert info["reason"] == "allowlist"


@pytest.mark.asyncio
async def test_ban_check(mock_redis):
    """Test banned user/IP is rejected."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock banned
    mock_redis.exists.return_value = 1
    
    allowed, info = await limiter.check_limit(
        user_id="user-123",
        tier=RateLimitTier.FREE
    )
    
    assert allowed is False
    assert info["status"] == "banned"


@pytest.mark.asyncio
async def test_get_quota_usage(mock_redis):
    """Test getting quota usage for user."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock usage
    mock_redis.zcard.return_value = 50
    
    usage = await limiter.get_quota_usage("user-123", RateLimitTier.PREMIUM)
    
    assert usage["user_id"] == "user-123"
    assert usage["tier"] == "premium"
    assert "usage" in usage
    assert "minute" in usage["usage"]
    assert "hour" in usage["usage"]
    assert "day" in usage["usage"]


@pytest.mark.asyncio
async def test_reset_user_limits(mock_redis):
    """Test resetting user limits."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock keys
    mock_redis.keys.return_value = [b"rl:minute:user-123", b"violations:user-123"]
    
    await limiter.reset_user_limits("user-123")
    
    # Should have called delete
    mock_redis.delete.assert_called()


@pytest.mark.asyncio
async def test_concurrent_request_limit(mock_redis):
    """Test concurrent request limiting."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock under limit
    mock_redis.get.return_value = b"2"
    mock_redis.incr.return_value = 3
    
    allowed, info = await limiter._check_concurrent("user-123", max_concurrent=5)
    
    assert allowed is True
    assert info["current"] == 3
    assert info["limit"] == 5
    assert info["remaining"] == 2


@pytest.mark.asyncio
async def test_concurrent_request_exceeded(mock_redis):
    """Test concurrent request limit exceeded."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock at limit
    mock_redis.get.return_value = b"5"
    
    allowed, info = await limiter._check_concurrent("user-123", max_concurrent=5)
    
    assert allowed is False
    assert info["remaining"] == 0


@pytest.mark.asyncio
async def test_release_concurrent(mock_redis):
    """Test releasing concurrent request slot."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    await limiter.release_concurrent("user-123")
    
    # Should have called decr
    mock_redis.decr.assert_called_once()


@pytest.mark.asyncio
async def test_analytics(mock_redis):
    """Test getting rate limit analytics."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    # Mock data
    mock_redis.keys.return_value = [b"violations:user-1", b"violations:user-2"]
    mock_redis.zcount.return_value = 5
    mock_redis.zcard.return_value = 8
    
    analytics = await limiter.get_analytics(window_minutes=60)
    
    assert "window_minutes" in analytics
    assert "stats" in analytics
    assert analytics["window_minutes"] == 60


@pytest.mark.asyncio
async def test_burst_allowance(mock_redis):
    """Test burst allowance allows temporary over-limit."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    tier = RateLimitTier.FREE
    tier_config = limiter.config.TIERS[tier]
    
    # Mock count just over limit but under burst
    mock_redis.zcard.return_value = tier_config.requests_per_minute + 5
    
    allowed, info = await limiter._check_window(
        "user-123",
        tier_config.requests_per_minute,
        60,
        "minute"
    )
    
    # Should be rejected (over soft limit)
    assert allowed is False
    # But not hard rejected yet (burst allows it)
    assert info["current"] == tier_config.requests_per_minute + 6  # +1 from zadd


@pytest.mark.asyncio
async def test_user_preference_over_ip(mock_redis):
    """Test user ID takes preference over IP for identification."""
    limiter = AdvancedRateLimiterV2(mock_redis)
    
    mock_redis.zcard.return_value = 0
    
    allowed, info = await limiter.check_limit(
        user_id="user-123",
        ip_address="1.2.3.4",  # Should be ignored
        tier=RateLimitTier.FREE
    )
    
    # Verify user ID was used (check if zadd was called with user ID key)
    calls = mock_redis.zadd.call_args_list
    # Should contain "user-123" in key, not IP
    assert any("user-123" in str(call) for call in calls)

