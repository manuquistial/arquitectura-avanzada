"""
Circuit Breaker Pattern Implementation
Protects against cascading failures in distributed systems
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Any, TypeVar, Generic
from threading import Lock

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes to close from half-open
    timeout: float = 60.0               # Seconds before trying half-open
    expected_exception: type = Exception # Exception type to catch
    
    # Advanced settings
    half_open_max_calls: int = 1        # Max calls in half-open state
    sliding_window_size: int = 10       # Rolling window for failure rate
    failure_rate_threshold: float = 0.5 # Failure rate to open (0.0-1.0)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker(Generic[T]):
    """
    Circuit Breaker implementation.
    
    Protects external service calls from cascading failures.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered, limited requests
    
    Usage:
        cb = CircuitBreaker("external_service", config)
        
        # With decorator
        @cb.call
        def external_call():
            return requests.get("https://external-api.com")
        
        # With context manager
        with cb:
            result = external_call()
        
        # Manual
        try:
            result = cb.call(external_call)
        except CircuitBreakerError:
            # Circuit is open, use fallback
            result = fallback_value
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[..., T]] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging/metrics)
            config: Configuration (uses defaults if None)
            fallback: Fallback function when circuit is open
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # Sliding window for failure rate calculation
        self._call_history: list[bool] = []  # True = success, False = failure
        
        # Thread safety
        self._lock = Lock()
        
        logger.info(f"Circuit breaker initialized: {name} (state: {self._state.value})")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._update_state()
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == CircuitState.HALF_OPEN
    
    def _update_state(self):
        """Update circuit state based on conditions."""
        if self._state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    logger.info(f"Circuit breaker {self.name}: OPEN → HALF_OPEN (timeout elapsed)")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
    
    def _record_success(self):
        """Record successful call."""
        with self._lock:
            self._call_history.append(True)
            self._trim_history()
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(f"Circuit breaker {self.name}: Success in HALF_OPEN ({self._success_count}/{self.config.success_threshold})")
                
                if self._success_count >= self.config.success_threshold:
                    logger.info(f"Circuit breaker {self.name}: HALF_OPEN → CLOSED (threshold met)")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._last_failure_time = None
            
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    def _record_failure(self):
        """Record failed call."""
        with self._lock:
            self._call_history.append(False)
            self._trim_history()
            
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker {self.name}: Failure in HALF_OPEN → OPEN")
                self._state = CircuitState.OPEN
                self._success_count = 0
            
            elif self._state == CircuitState.CLOSED:
                # Check failure threshold
                if self._failure_count >= self.config.failure_threshold:
                    logger.error(f"Circuit breaker {self.name}: CLOSED → OPEN (threshold {self._failure_count}/{self.config.failure_threshold})")
                    self._state = CircuitState.OPEN
                
                # Check failure rate
                failure_rate = self._calculate_failure_rate()
                if failure_rate >= self.config.failure_rate_threshold:
                    logger.error(f"Circuit breaker {self.name}: CLOSED → OPEN (failure rate {failure_rate:.2%})")
                    self._state = CircuitState.OPEN
    
    def _trim_history(self):
        """Trim call history to sliding window size."""
        if len(self._call_history) > self.config.sliding_window_size:
            self._call_history = self._call_history[-self.config.sliding_window_size:]
    
    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate from call history."""
        if not self._call_history:
            return 0.0
        
        failures = sum(1 for success in self._call_history if not success)
        return failures / len(self._call_history)
    
    def _can_attempt_call(self) -> bool:
        """Check if call can be attempted."""
        with self._lock:
            self._update_state()
            
            if self._state == CircuitState.CLOSED:
                return True
            
            elif self._state == CircuitState.HALF_OPEN:
                # Limit calls in half-open state
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            else:  # OPEN
                return False
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args, **kwargs: Function arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If call fails and circuit remains closed
        """
        if not self._can_attempt_call():
            logger.warning(f"Circuit breaker {self.name} is OPEN, call blocked")
            
            if self.fallback:
                logger.info(f"Circuit breaker {self.name}: Using fallback")
                return self.fallback(*args, **kwargs)
            
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except self.config.expected_exception as e:
            logger.warning(f"Circuit breaker {self.name}: Call failed - {e}")
            self._record_failure()
            
            if self.is_open and self.fallback:
                logger.info(f"Circuit breaker {self.name}: Circuit now OPEN, using fallback")
                return self.fallback(*args, **kwargs)
            
            raise
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper
    
    @contextmanager
    def protect(self):
        """Context manager for circuit breaker."""
        if not self._can_attempt_call():
            if self.fallback:
                yield self.fallback
                return
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            yield
            self._record_success()
        except self.config.expected_exception as e:
            self._record_failure()
            if self.is_open and self.fallback:
                yield self.fallback
            else:
                raise
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"Circuit breaker {self.name}: Manual reset to CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            self._call_history.clear()
    
    def force_open(self):
        """Manually force circuit breaker to OPEN state."""
        with self._lock:
            logger.warning(f"Circuit breaker {self.name}: Forced to OPEN")
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_rate": self._calculate_failure_rate(),
                "last_failure_time": self._last_failure_time,
                "call_history_size": len(self._call_history)
            }
    
    def __repr__(self):
        return f"CircuitBreaker(name={self.name}, state={self._state.value})"


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Usage:
        registry = CircuitBreakerRegistry()
        
        # Get or create circuit breaker
        cb = registry.get("mintic_hub")
        
        # Use circuit breaker
        result = cb.call(external_api_call)
        
        # Get all stats
        all_stats = registry.get_all_stats()
    """
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()
    
    def get(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration (only used if creating new)
            fallback: Fallback function (only used if creating new)
        
        Returns:
            Circuit breaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config, fallback)
            return self._breakers[name]
    
    def remove(self, name: str):
        """Remove circuit breaker from registry."""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
    
    def get_all_stats(self) -> dict[str, dict]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global registry instance
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
) -> CircuitBreaker:
    """Get circuit breaker from global registry."""
    return _global_registry.get(name, config, fallback)


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """
    Decorator for circuit breaker.
    
    Usage:
        @circuit_breaker("external_api", config=my_config)
        def call_external_api():
            return requests.get("https://api.example.com")
    """
    cb = get_circuit_breaker(name, config, fallback)
    return cb


# Convenience function for getting all stats (for monitoring endpoint)
def get_all_circuit_breaker_stats() -> dict[str, dict]:
    """Get stats for all circuit breakers (for /metrics endpoint)."""
    return _global_registry.get_all_stats()
