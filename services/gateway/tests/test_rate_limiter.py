"""Tests for advanced rate limiter."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from app.rate_limiter import AdvancedRateLimiter, RateLimiterConfig


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.zadd = AsyncMock(return_value=1)
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.keys = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis."""
    limiter = AdvancedRateLimiter(redis_client=mock_redis)
    return limiter


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "192.168.1.100"
    return request


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit(rate_limiter, mock_request, mock_redis):
    """Test that requests within limit are allowed."""
    # Simulate count within limit
    mock_redis.incr.return_value = 10
    
    result = await rate_limiter.check_request(mock_request)
    
    assert result is None  # No error = allowed


@pytest.mark.asyncio
async def test_rate_limiter_rejects_over_limit(rate_limiter, mock_request, mock_redis):
    """Test that requests over limit are rejected."""
    # Simulate count over limit (default is 60)
    mock_redis.incr.return_value = 61
    
    result = await rate_limiter.check_request(mock_request)
    
    assert result is not None
    assert result["error"] == "Rate limit exceeded"
    assert result["limit"] == 60


@pytest.mark.asyncio
async def test_rate_limiter_role_based_limits(rate_limiter, mock_request, mock_redis):
    """Test role-based rate limits."""
    # Set role to operador (200 rpm)
    mock_request.headers = {"X-User-Role": "operador"}
    
    # Simulate count at 150 (within operador limit)
    mock_redis.incr.return_value = 150
    
    result = await rate_limiter.check_request(mock_request)
    assert result is None  # Allowed
    
    # Now exceed operador limit
    mock_redis.incr.return_value = 201
    result = await rate_limiter.check_request(mock_request)
    assert result is not None
    assert result["limit"] == 200


@pytest.mark.asyncio
async def test_rate_limiter_bans_after_violations(rate_limiter, mock_request, mock_redis):
    """Test that IP is banned after threshold violations."""
    # Simulate threshold violations
    mock_redis.incr.return_value = 61  # Over limit
    mock_redis.zcard.return_value = 5  # 5 violations
    
    result = await rate_limiter.check_request(mock_request)
    
    # Should trigger ban
    assert mock_redis.setex.called
    assert result["violations"] == 5


@pytest.mark.asyncio
async def test_rate_limiter_rejects_banned_ip(rate_limiter, mock_request, mock_redis):
    """Test that banned IP is rejected."""
    # Simulate banned IP
    mock_redis.exists.return_value = 1
    
    result = await rate_limiter.check_request(mock_request)
    
    assert result is not None
    assert result["error"] == "IP banned"


@pytest.mark.asyncio
async def test_rate_limiter_allowlist(rate_limiter, mock_request):
    """Test that allowlisted IPs bypass rate limiting."""
    # Set IP to allowlisted address
    mock_request.client.host = "127.0.0.1"
    
    result = await rate_limiter.check_request(mock_request)
    
    assert result is None  # Always allowed


@pytest.mark.asyncio
async def test_rate_limiter_exempt_routes(rate_limiter, mock_request):
    """Test that exempt routes bypass rate limiting."""
    # Set to exempt route
    mock_request.url.path = "/health"
    
    result = await rate_limiter.check_request(mock_request)
    
    assert result is None  # Always allowed


@pytest.mark.asyncio
async def test_rate_limiter_sliding_window(rate_limiter, mock_request, mock_redis):
    """Test sliding window implementation."""
    # First request
    mock_redis.incr.return_value = 1
    
    result = await rate_limiter.check_request(mock_request)
    assert result is None
    
    # Verify Redis key format: rl:{route}:{role}:{ip}:{bucket}
    call_args = mock_redis.incr.call_args[0][0]
    assert call_args.startswith("rl:/api/test:default:192.168.1.100:")


@pytest.mark.asyncio
async def test_get_status(rate_limiter, mock_redis):
    """Test get_status method."""
    mock_redis.zcard.return_value = 2
    mock_redis.keys.return_value = []
    
    status = await rate_limiter.get_status("192.168.1.100")
    
    assert status["redis_available"] is True
    assert "config" in status
    assert status["config"]["limits"]["ciudadano"] == 60
    assert status["config"]["limits"]["operador"] == 200
    assert status["config"]["limits"]["mintic_client"] == 400
    assert "ip_status" in status
    assert status["ip_status"]["violations"] == 2


@pytest.mark.asyncio
async def test_mintic_client_high_limit(rate_limiter, mock_request, mock_redis):
    """Test that mintic_client gets 400 rpm limit."""
    mock_request.headers = {"X-Service-Name": "mintic_client"}
    mock_redis.incr.return_value = 350
    
    result = await rate_limiter.check_request(mock_request)
    assert result is None  # Within 400 rpm limit
    
    mock_redis.incr.return_value = 401
    result = await rate_limiter.check_request(mock_request)
    assert result is not None
    assert result["limit"] == 400


@pytest.mark.asyncio
async def test_transfer_high_limit(rate_limiter, mock_request, mock_redis):
    """Test that transfer service gets 400 rpm limit."""
    mock_request.headers = {"X-Service-Name": "transfer"}
    mock_redis.incr.return_value = 350
    
    result = await rate_limiter.check_request(mock_request)
    assert result is None  # Within 400 rpm limit

