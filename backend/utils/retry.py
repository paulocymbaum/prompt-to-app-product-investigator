"""
Retry utilities with exponential backoff for external service calls.

This module provides decorators and functions for retrying failed operations
with configurable backoff strategies.
"""

import asyncio
import functools
import random
from typing import Any, Callable, Optional, Type, Tuple
import structlog

logger = structlog.get_logger()


def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @exponential_backoff(max_retries=3, base_delay=1.0)
        async def call_external_api():
            response = await client.post(url)
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt == max_retries:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt + 1,
                            max_retries=max_retries,
                            error=str(e)
                        )
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=round(delay, 2),
                        error=str(e)
                    )
                    
                    await asyncio.sleep(delay)
            
            # Raise the last exception if all retries failed
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt + 1,
                            max_retries=max_retries,
                            error=str(e)
                        )
                        break
                    
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=round(delay, 2),
                        error=str(e)
                    )
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for failing external services.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def call_service():
            async with breaker:
                return await external_service.call()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = structlog.get_logger()
    
    async def __aenter__(self):
        """Enter circuit breaker context."""
        import time
        
        if self.state == "OPEN":
            # Check if timeout has passed
            if time.time() - self.last_failure_time >= self.timeout:
                self.logger.info("circuit_breaker_half_open")
                self.state = "HALF_OPEN"
                self.failure_count = 0
            else:
                self.logger.warning("circuit_breaker_open")
                raise Exception(f"Circuit breaker is OPEN. Service unavailable for {self.timeout}s.")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context."""
        import time
        
        if exc_type and issubclass(exc_type, self.expected_exception):
            # Failure occurred
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.logger.error(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
                self.state = "OPEN"
            
            return False  # Propagate exception
        else:
            # Success
            if self.state == "HALF_OPEN":
                self.logger.info("circuit_breaker_closed")
                self.state = "CLOSED"
                self.failure_count = 0
            
            return False


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retries
        base_delay: Initial delay between retries
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of successful function call
    
    Raises:
        Last exception if all retries fail
    """
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise
            
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "retrying_function",
                function=func.__name__,
                attempt=attempt + 1,
                delay=delay
            )
            await asyncio.sleep(delay)
