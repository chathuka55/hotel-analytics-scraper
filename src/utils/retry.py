"""Retry logic with exponential backoff for resilient scraping."""

import functools
import time
from typing import Any, Callable, Optional, Tuple, Type, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
    before_sleep_log,
)

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 2
DEFAULT_MAX_DELAY = 60
DEFAULT_EXPONENTIAL_BASE = 2

# Exceptions that typically warrant a retry
RETRIABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def get_retry_config(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exponential_base: Optional[float] = None,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable] = None,
):
    """Create a tenacity retry configuration.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to retry on
        on_retry: Callback function to call on each retry

    Returns:
        tenacity.Retrying: Configured retry object
    """
    max_retries = max_retries or DEFAULT_MAX_RETRIES
    base_delay = base_delay or DEFAULT_BASE_DELAY
    max_delay = max_delay or DEFAULT_MAX_DELAY
    exponential_base = exponential_base or DEFAULT_EXPONENTIAL_BASE
    retry_exceptions = exceptions or RETRIABLE_EXCEPTIONS

    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(
            multiplier=base_delay,
            max=max_delay,
            exp_base=exponential_base,
        ),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True,
    )


def with_retry(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exponential_base: Optional[float] = None,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """Decorator to add retry logic with exponential backoff.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential backoff base
        exceptions: Exceptions to retry on

    Returns:
        Decorator function

    Example:
        @with_retry(max_retries=3, base_delay=2)
        def fetch_data():
            return requests.get(url)
    """
    config = get_retry_config(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        exceptions=exceptions,
    )
    return config


def retry_with_backoff(
    func: Callable,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: Tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS,
    *args,
    **kwargs,
) -> Any:
    """Execute a function with manual retry and exponential backoff.

    Args:
        func: Function to execute
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay
        exceptions: Exceptions to catch and retry
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        Last exception encountered after all retries exhausted
    """
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                # Calculate delay with exponential backoff and jitter
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = time.time() % 1  # Simple jitter
                total_delay = delay + jitter

                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed for {func.__name__}: {e}. "
                    f"Retrying in {total_delay:.1f}s..."
                )
                time.sleep(total_delay)
            else:
                logger.error(
                    f"All {max_retries} attempts failed for {func.__name__}: {e}"
                )

    raise last_exception


class RetryContext:
    """Context manager for retry operations with state tracking."""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        exceptions: Tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions
        self.attempt = 0
        self.last_error: Optional[Exception] = None
        self.is_success = False

    def should_retry(self, exception: Exception) -> bool:
        """Check if we should retry after an exception."""
        if not isinstance(exception, self.exceptions):
            return False
        if self.attempt >= self.max_retries:
            return False
        return True

    def get_delay(self) -> float:
        """Calculate delay for current attempt."""
        delay = min(self.base_delay * (2 ** (self.attempt - 1)), self.max_delay)
        jitter = time.time() % 1
        return delay + jitter

    def __enter__(self):
        self.attempt = 0
        self.last_error = None
        self.is_success = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.is_success = True
            return True

        self.attempt += 1
        self.last_error = exc_val

        if self.should_retry(exc_val):
            delay = self.get_delay()
            logger.warning(
                f"Retry {self.attempt}/{self.max_retries} after error: {exc_val}. "
                f"Waiting {delay:.1f}s..."
            )
            time.sleep(delay)
            # Don't suppress the exception - let the caller retry
            return False

        # All retries exhausted
        logger.error(f"Failed after {self.attempt} attempts: {exc_val}")
        return False  # Let the exception propagate
