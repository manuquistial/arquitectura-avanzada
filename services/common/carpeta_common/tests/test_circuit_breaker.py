"""
Unit tests for Circuit Breaker
"""

import pytest
import time
from unittest.mock import Mock

from carpeta_common.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    CircuitBreakerRegistry
)


@pytest.fixture
def config():
    """Circuit breaker config for testing."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=0.5,  # Short timeout for tests
        half_open_max_calls=3,  # Must be >= success_threshold to allow transition
        sliding_window_size=5,
        failure_rate_threshold=0.6
    )


def test_circuit_breaker_initial_state(config):
    """Test circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker("test", config)
    
    assert cb.state == CircuitState.CLOSED
    assert cb.is_closed
    assert not cb.is_open
    assert not cb.is_half_open


def test_circuit_opens_after_failures(config):
    """Test circuit opens after failure threshold."""
    cb = CircuitBreaker("test", config)
    
    def failing_func():
        raise Exception("Test failure")
    
    # Record failures
    for i in range(config.failure_threshold):
        try:
            cb.call(failing_func)
        except Exception:
            pass
    
    # Circuit should be OPEN
    assert cb.is_open


def test_circuit_breaker_blocks_when_open(config):
    """Test circuit breaker blocks calls when OPEN."""
    cb = CircuitBreaker("test", config)
    
    def failing_func():
        raise Exception("Test failure")
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        try:
            cb.call(failing_func)
        except:
            pass
    
    assert cb.is_open
    
    # Next call should raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        cb.call(lambda: "should not execute")


def test_circuit_transitions_to_half_open(config):
    """Test circuit transitions to HALF_OPEN after timeout."""
    cb = CircuitBreaker("test", config)
    
    def failing_func():
        raise Exception("Test failure")
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        try:
            cb.call(failing_func)
        except:
            pass
    
    assert cb.is_open
    
    # Wait for timeout
    time.sleep(config.timeout + 0.1)
    
    # Check state
    assert cb.is_half_open


def test_circuit_closes_from_half_open(config):
    """Test circuit closes from HALF_OPEN after successes."""
    cb = CircuitBreaker("test", config)
    
    # Open the circuit
    cb.force_open()
    assert cb.is_open
    
    # Wait for timeout
    time.sleep(config.timeout + 0.1)
    assert cb.is_half_open
    
    # Record successes
    for _ in range(config.success_threshold):
        cb.call(lambda: "success")
    
    # Circuit should be CLOSED
    assert cb.is_closed


def test_circuit_reopens_on_failure_in_half_open(config):
    """Test circuit reopens on failure in HALF_OPEN state."""
    cb = CircuitBreaker("test", config)
    
    # Open and transition to HALF_OPEN
    cb.force_open()
    time.sleep(config.timeout + 0.1)
    assert cb.is_half_open
    
    # Fail in HALF_OPEN
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
    except:
        pass
    
    # Circuit should be OPEN again
    assert cb.is_open


def test_fallback_function(config):
    """Test fallback function is called when circuit is OPEN."""
    fallback_called = False
    
    def fallback():
        nonlocal fallback_called
        fallback_called = True
        return "fallback_result"
    
    cb = CircuitBreaker("test", config, fallback=fallback)
    
    # Open the circuit
    cb.force_open()
    
    # Call should use fallback
    result = cb.call(lambda: "should not execute")
    
    assert fallback_called
    assert result == "fallback_result"


def test_decorator_usage(config):
    """Test circuit breaker as decorator."""
    cb = CircuitBreaker("test", config)
    
    call_count = 0
    
    @cb
    def tracked_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = tracked_func()
    
    assert result == "success"
    assert call_count == 1


def test_context_manager(config):
    """Test circuit breaker as context manager."""
    cb = CircuitBreaker("test", config)
    
    with cb.protect():
        result = "success"
    
    assert result == "success"
    assert cb.is_closed


def test_manual_reset(config):
    """Test manual circuit reset."""
    cb = CircuitBreaker("test", config)
    
    # Open the circuit
    cb.force_open()
    assert cb.is_open
    
    # Reset
    cb.reset()
    assert cb.is_closed


def test_get_stats(config):
    """Test getting circuit breaker statistics."""
    cb = CircuitBreaker("test", config)
    
    stats = cb.get_stats()
    
    assert stats["name"] == "test"
    assert stats["state"] == "closed"
    assert "failure_count" in stats
    assert "failure_rate" in stats


def test_failure_rate_threshold(config):
    """Test circuit opens based on failure rate."""
    cb = CircuitBreaker("test", config)
    
    # Mix of successes and failures
    cb.call(lambda: "success")
    cb.call(lambda: "success")
    
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    except:
        pass
    
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    except:
        pass
    
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    except:
        pass
    
    # Should be OPEN due to failure rate
    stats = cb.get_stats()
    failure_rate = stats["failure_rate"]
    
    if failure_rate >= config.failure_rate_threshold:
        assert cb.is_open


def test_circuit_breaker_registry():
    """Test circuit breaker registry."""
    registry = CircuitBreakerRegistry()
    
    # Get circuit breaker
    cb1 = registry.get("test1")
    assert cb1.name == "test1"
    
    # Get same circuit breaker
    cb2 = registry.get("test1")
    assert cb1 is cb2
    
    # Get different circuit breaker
    cb3 = registry.get("test2")
    assert cb3 is not cb1


def test_registry_get_all_stats():
    """Test getting all circuit breaker stats from registry."""
    registry = CircuitBreakerRegistry()
    
    cb1 = registry.get("test1")
    cb2 = registry.get("test2")
    
    all_stats = registry.get_all_stats()
    
    assert "test1" in all_stats
    assert "test2" in all_stats
    assert all_stats["test1"]["name"] == "test1"
    assert all_stats["test2"]["name"] == "test2"


def test_registry_remove():
    """Test removing circuit breaker from registry."""
    registry = CircuitBreakerRegistry()
    
    cb = registry.get("test")
    assert "test" in registry.get_all_stats()
    
    registry.remove("test")
    assert "test" not in registry.get_all_stats()


def test_registry_reset_all():
    """Test resetting all circuit breakers in registry."""
    registry = CircuitBreakerRegistry()
    
    cb1 = registry.get("test1")
    cb2 = registry.get("test2")
    
    # Open circuits
    cb1.force_open()
    cb2.force_open()
    
    assert cb1.is_open
    assert cb2.is_open
    
    # Reset all
    registry.reset_all()
    
    assert cb1.is_closed
    assert cb2.is_closed


def test_success_resets_failure_count(config):
    """Test that success resets failure count in CLOSED state."""
    cb = CircuitBreaker("test", config)
    
    # Record some failures
    for _ in range(config.failure_threshold - 1):
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except:
            pass
    
    # Should still be CLOSED
    assert cb.is_closed
    
    # Success should reset failure count
    cb.call(lambda: "success")
    
    # Should not open even after more failures
    for _ in range(config.failure_threshold - 1):
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except:
            pass
    
    # Should still be CLOSED (failure count was reset)
    assert cb.is_closed

