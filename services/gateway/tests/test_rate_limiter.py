"""Tests for rate limiter - Simplified for common package usage."""

import pytest

def test_rate_limiter_available():
    """Test that rate limiter can be imported from common package."""
    from carpeta_common.advanced_rate_limiter import AdvancedRateLimiterV2, RateLimiterTier
    
    assert AdvancedRateLimiterV2 is not None
    assert RateLimiterTier is not None
    assert hasattr(RateLimiterTier, 'FREE')
    assert hasattr(RateLimiterTier, 'BASIC')
    assert hasattr(RateLimiterTier, 'PREMIUM')
    assert hasattr(RateLimiterTier, 'ENTERPRISE')

# Note: Detailed rate limiter tests are in services/common/carpeta_common/tests/test_advanced_rate_limiter.py
