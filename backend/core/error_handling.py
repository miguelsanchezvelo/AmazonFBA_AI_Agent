#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust Error Handling - Retry Logic, Circuit Breakers, Graceful Degradation

Provides:
- Exponential backoff retry logic
- Circuit breaker pattern for external services
- Graceful degradation with fallback options
- Error categorization and logging
- Recovery strategies

Usage:
    @retry_with_exponential_backoff(max_retries=3)
    async def call_external_api():
        pass
    
    circuit = CircuitBreaker("external_api", failure_threshold=5)
    try:
        result = await circuit.call(api_call)
    except CircuitBreakerOpen:
        # Use fallback data
        result = get_fallback_data()
"""

from typing import Any, Callable, Optional, Type, TypeVar, Coroutine, List
from functools import wraps
import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorCategory(Enum):
    """Error categorization."""
    TRANSIENT = "transient"        # Temporary, retry
    PERMANENT = "permanent"        # Permanent, don't retry
    EXTERNAL_SERVICE = "external"  # External service issue
    DATABASE = "database"          # Database issue
    AUTH = "auth"                  # Authentication issue
    RATE_LIMIT = "rate_limit"      # Rate limit hit
    CONFIG = "config"              # Configuration issue


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Exponential backoff multiplier
            jitter: Add randomness to delays
            retryable_exceptions: Exceptions that trigger retry
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            Exception  # Retry on any exception by default
        ]
    
    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt number."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        backoff_factor: Backoff multiplier
        jitter: Add randomness to delays
    """
    config = RetryConfig(max_retries, initial_delay, max_delay, backoff_factor, jitter)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {config.max_retries + 1} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject calls
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls.
    
    States:
    - CLOSED: Normal operation, all calls go through
    - OPEN: Too many failures, reject calls immediately
    - HALF_OPEN: Recovery testing, allow limited calls
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening
            recovery_timeout: Seconds before half-open attempt
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_attempt_time: Optional[datetime] = None
    
    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpen(f"Circuit breaker {self.name} is OPEN")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info(f"Circuit breaker {self.name} CLOSED after recovery")
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                f"Circuit breaker {self.name} OPEN after {self.failure_count} failures"
            )
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.name} reopened during recovery")
    
    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class FallbackProvider:
    """
    Provides fallback data when primary source fails.
    
    Used for graceful degradation:
    - Cache data when API unavailable
    - Mock data when cache unavailable
    - Partial results when some components fail
    """
    
    def __init__(self, name: str):
        """Initialize fallback provider."""
        self.name = name
        self.fallback_data: Optional[Any] = None
        self.last_update: Optional[datetime] = None
        self.max_age_seconds: int = 3600  # 1 hour default
    
    def set_fallback(self, data: Any, max_age_seconds: int = 3600) -> None:
        """Set fallback data."""
        self.fallback_data = data
        self.last_update = datetime.now()
        self.max_age_seconds = max_age_seconds
    
    def get_fallback(self) -> Optional[Any]:
        """Get fallback data if available and not stale."""
        if not self.fallback_data or not self.last_update:
            return None
        
        age = (datetime.now() - self.last_update).total_seconds()
        if age > self.max_age_seconds:
            logger.warning(f"Fallback data for {self.name} is stale ({age:.0f}s old)")
            return None
        
        logger.info(f"Using fallback data for {self.name}")
        return self.fallback_data
    
    async def call_with_fallback(
        self,
        primary_func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Call primary function with fallback.
        
        Args:
            primary_func: Primary function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Primary result or fallback if primary fails
        """
        try:
            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = primary_func(*args, **kwargs)
            
            # Update fallback cache on success
            self.set_fallback(result)
            return result
        
        except Exception as e:
            logger.warning(f"Primary call failed for {self.name}: {e}, using fallback")
            
            fallback = self.get_fallback()
            if fallback is not None:
                return fallback
            
            logger.error(f"No fallback available for {self.name}")
            raise


class ErrorRecoveryStrategy:
    """Strategy for recovering from specific errors."""
    
    @staticmethod
    def categorize_error(error: Exception) -> ErrorCategory:
        """Categorize error type."""
        error_name = type(error).__name__.lower()
        
        if "timeout" in error_name or "connection" in error_name:
            return ErrorCategory.TRANSIENT
        elif "401" in str(error) or "unauthorized" in error_name:
            return ErrorCategory.AUTH
        elif "429" in str(error):
            return ErrorCategory.RATE_LIMIT
        elif "database" in error_name or "sql" in error_name:
            return ErrorCategory.DATABASE
        elif "config" in error_name:
            return ErrorCategory.CONFIG
        else:
            return ErrorCategory.EXTERNAL_SERVICE
    
    @staticmethod
    def should_retry(error: Exception) -> bool:
        """Determine if error should trigger retry."""
        category = ErrorRecoveryStrategy.categorize_error(error)
        return category in [
            ErrorCategory.TRANSIENT,
            ErrorCategory.EXTERNAL_SERVICE,
            ErrorCategory.RATE_LIMIT
        ]
    
    @staticmethod
    def get_recovery_action(error: Exception) -> str:
        """Get recommended recovery action."""
        category = ErrorRecoveryStrategy.categorize_error(error)
        
        actions = {
            ErrorCategory.TRANSIENT: "Retry with exponential backoff",
            ErrorCategory.PERMANENT: "Log error and skip",
            ErrorCategory.EXTERNAL_SERVICE: "Open circuit breaker, use fallback",
            ErrorCategory.DATABASE: "Retry with backoff, check connection",
            ErrorCategory.AUTH: "Check credentials, update token",
            ErrorCategory.RATE_LIMIT: "Wait and retry with longer delay",
            ErrorCategory.CONFIG: "Check configuration, fix and restart"
        }
        
        return actions.get(category, "Log and skip")


# Export commonly used functions
__all__ = [
    "retry_with_exponential_backoff",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "FallbackProvider",
    "ErrorRecoveryStrategy",
    "ErrorCategory"
]

