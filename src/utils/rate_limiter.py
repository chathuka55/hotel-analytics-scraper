"""Rate limiting utilities to prevent overwhelming target servers."""

import asyncio
import random
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from threading import RLock
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for controlling request frequency.

    Supports both sync and async usage patterns.
    """

    def __init__(
        self,
        requests_per_second: float = 0.5,
        burst_size: Optional[int] = None,
        min_delay: float = 1.0,
        max_delay: float = 10.0,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst of requests allowed
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests
        """
        self._rate = requests_per_second
        self._burst = burst_size or max(1, int(requests_per_second * 2))
        self._min_delay = min_delay
        self._max_delay = max_delay

        # Token bucket state
        self._tokens = float(self._burst)
        self._last_update = time.time()
        self._lock = RLock()

        # Request history for adaptive limiting
        self._request_times: deque[float] = deque(maxlen=100)
        self._error_count = 0

    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self._burst,
            self._tokens + elapsed * self._rate,
        )
        self._last_update = now

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire a token (sync version).

        Args:
            blocking: Whether to block until a token is available
            timeout: Maximum time to wait for a token

        Returns:
            True if token acquired, False otherwise
        """
        with self._lock:
            self._add_tokens()

            if self._tokens >= 1:
                self._tokens -= 1
                self._request_times.append(time.time())
                return True

            if not blocking:
                return False

            # Calculate wait time
            tokens_needed = 1 - self._tokens
            wait_time = tokens_needed / self._rate

            if timeout is not None and wait_time > timeout:
                return False

        # Wait outside the lock
        jitter = random.uniform(0, 0.5)
        time.sleep(wait_time + jitter)

        with self._lock:
            self._add_tokens()
            if self._tokens >= 1:
                self._tokens -= 1
                self._request_times.append(time.time())
                return True
            return False

    async def acquire_async(
        self, blocking: bool = True, timeout: Optional[float] = None
    ) -> bool:
        """Acquire a token (async version).

        Args:
            blocking: Whether to block until a token is available
            timeout: Maximum time to wait

        Returns:
            True if token acquired, False otherwise
        """
        with self._lock:
            self._add_tokens()

            if self._tokens >= 1:
                self._tokens -= 1
                self._request_times.append(time.time())
                return True

            if not blocking:
                return False

            tokens_needed = 1 - self._tokens
            wait_time = tokens_needed / self._rate

            if timeout is not None and wait_time > timeout:
                return False

        jitter = random.uniform(0, 0.5)
        await asyncio.sleep(wait_time + jitter)

        with self._lock:
            self._add_tokens()
            if self._tokens >= 1:
                self._tokens -= 1
                self._request_times.append(time.time())
                return True
            return False

    def get_current_delay(self) -> float:
        """Get the current recommended delay."""
        with self._lock:
            self._add_tokens()
            if self._tokens >= 1:
                return self._min_delay
            return min(self._max_delay, (1 - self._tokens) / self._rate)

    def record_error(self) -> None:
        """Record an error to potentially slow down."""
        with self._lock:
            self._error_count += 1
            if self._error_count > 3:
                # Back off by reducing rate temporarily
                self._rate = max(0.1, self._rate * 0.8)
                self._error_count = 0

    def record_success(self) -> None:
        """Record a success to potentially speed up."""
        with self._lock:
            self._error_count = max(0, self._error_count - 1)

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        with self._lock:
            recent_requests = len(
                [t for t in self._request_times if time.time() - t < 60]
            )
            return {
                "current_tokens": round(self._tokens, 2),
                "rate_per_second": round(self._rate, 2),
                "requests_last_minute": recent_requests,
                "current_delay": round(self.get_current_delay(), 2),
            }


# Context managers for easy usage

@contextmanager
def rate_limited(limiter: RateLimiter):
    """Context manager for sync rate limiting."""
    limiter.acquire()
    try:
        yield
    except Exception:
        limiter.record_error()
        raise
    else:
        limiter.record_success()


@asynccontextmanager
async def async_rate_limited(limiter: RateLimiter):
    """Context manager for async rate limiting."""
    await limiter.acquire_async()
    try:
        yield
    except Exception:
        limiter.record_error()
        raise
    else:
        limiter.record_success()
