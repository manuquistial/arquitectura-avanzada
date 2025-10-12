"""Circuit Breaker pattern implementation.

Prevents cascading failures by failing fast when downstream services are unavailable.

States:
- CLOSED: Normal operation, all requests allowed
- OPEN: Failure threshold exceeded, all requests fail immediately
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import logging
import time
from enum import Enum
from typing import Callable, Optional, TypeVar, Any
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject requests
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls.
    
    Usage:
        breaker = CircuitBreaker(name="mintic_hub", failure_threshold=5, timeout=60)
        
        result = await breaker.call(async_function, arg1, arg2)
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging/metrics)
            failure_threshold: Failures before opening circuit
            success_threshold: Successes in HALF_OPEN to close circuit
            timeout: Seconds to wait before attempting HALF_OPEN
            half_open_max_calls: Max concurrent calls in HALF_OPEN state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.time_in_open = 0.0
        self.opened_at: Optional[float] = None
    
    async def call(self, func: Callable, *args, **kwargs) -> T:
        """Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is OPEN
            Exception: Original exception from function
        """
        self.total_calls += 1
        
        # Check if should attempt call
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info(f"🔄 [{self.name}] Transitioning to HALF_OPEN (timeout expired)")
                self._transition_to_half_open()
            else:
                # Still in OPEN state
                logger.warning(f"⛔ [{self.name}] Circuit OPEN, failing fast")
                raise CircuitBreakerError(f"Circuit breaker {self.name} is OPEN")
        
        # HALF_OPEN: Limit concurrent calls
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                logger.warning(f"⚠️  [{self.name}] HALF_OPEN max calls reached, rejecting")
                raise CircuitBreakerError(f"Circuit breaker {self.name} is testing recovery")
            
            self.half_open_calls += 1
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            
            # Success handling
            self._on_success()
            
            return result
            
        except Exception as e:
            # Failure handling
            self._on_failure()
            raise
        
        finally:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls -= 1
    
    def _on_success(self):
        """Handle successful call."""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"✅ [{self.name}] Success in HALF_OPEN "
                f"({self.success_count}/{self.success_threshold})"
            )
            
            if self.success_count >= self.success_threshold:
                logger.info(f"🟢 [{self.name}] Circuit CLOSED (recovered)")
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            logger.warning(
                f"⚠️  [{self.name}] Failure {self.failure_count}/{self.failure_threshold}"
            )
            
            if self.failure_count >= self.failure_threshold:
                logger.error(f"🔴 [{self.name}] Circuit OPENED (threshold exceeded)")
                self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            logger.error(f"🔴 [{self.name}] Failure in HALF_OPEN, reopening circuit")
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        self.success_count = 0
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        if self.opened_at:
            self.time_in_open += time.time() - self.opened_at
        
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
    
    def get_metrics(self) -> dict:
        """Get circuit breaker metrics.
        
        Returns:
            Metrics dict for monitoring
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_in_open_seconds": self.time_in_open,
            "is_open": self.state == CircuitState.OPEN,
            "is_half_open": self.state == CircuitState.HALF_OPEN
        }
    
    def reset(self):
        """Reset circuit breaker (for testing)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"🔄 [{self.name}] Circuit breaker reset")


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0
) -> CircuitBreaker:
    """Get or create circuit breaker by name.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        timeout: Timeout before HALF_OPEN attempt
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            timeout=timeout
        )
    
    return _circuit_breakers[name]


def get_all_circuit_breaker_metrics() -> list[dict]:
    """Get metrics from all circuit breakers.
    
    Returns:
        List of metrics dicts
    """
    return [cb.get_metrics() for cb in _circuit_breakers.values()]

