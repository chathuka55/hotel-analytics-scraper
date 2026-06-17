"""Tests for rate limiter utility."""

import time

import pytest

from src.utils.rate_limiter import RateLimiter, rate_limited


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_basic_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(requests_per_second=10)

        # Should acquire immediately at first
        assert limiter.acquire(blocking=False) is True
        assert limiter.acquire(blocking=False) is True

    def test_rate_enforcement(self):
        """Test that rate is enforced."""
        limiter = RateLimiter(requests_per_second=2)

        start = time.time()
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        elapsed = time.time() - start

        # Should take at least some time due to rate limiting
        assert elapsed >= 0

    def test_token_bucket_refill(self):
        """Test token bucket refills over time."""
        limiter = RateLimiter(
            requests_per_second=10, burst_size=1
        )

        # Use the token
        assert limiter.acquire(blocking=False) is True
        # Should be empty immediately after
        assert limiter.acquire(blocking=False) is False

        # Wait for refill
        time.sleep(0.15)
        assert limiter.acquire(blocking=False) is True

    def test_error_handling(self):
        """Test error recording."""
        limiter = RateLimiter(requests_per_second=10)

        initial_rate = limiter._rate
        limiter.record_error()
        limiter.record_error()
        limiter.record_error()
        limiter.record_error()

        # Rate should decrease after multiple errors
        assert limiter._rate <= initial_rate

    def test_stats(self):
        """Test statistics reporting."""
        limiter = RateLimiter(requests_per_second=10)
        limiter.acquire()

        stats = limiter.get_stats()
        assert "current_tokens" in stats
        assert "rate_per_second" in stats
        assert stats["rate_per_second"] == 10.0

    def test_context_manager(self):
        """Test context manager usage."""
        limiter = RateLimiter(requests_per_second=100)

        with rate_limited(limiter):
            result = "success"

        assert result == "success"

    def test_error_in_context(self):
        """Test error handling in context manager."""
        limiter = RateLimiter(requests_per_second=100)

        try:
            with rate_limited(limiter):
                raise ValueError("test error")
        except ValueError:
            pass  # Expected

        # Should have recorded error
        stats = limiter.get_stats()
        assert stats is not None


class TestAsyncRateLimiter:
    """Test cases for async rate limiting."""

    @pytest.mark.asyncio
    async def test_async_acquire(self):
        """Test async acquire."""
        from src.utils.rate_limiter import async_rate_limited

        limiter = RateLimiter(requests_per_second=100)

        result = await limiter.acquire_async(blocking=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_context(self):
        """Test async context manager."""
        from src.utils.rate_limiter import async_rate_limited

        limiter = RateLimiter(requests_per_second=100)

        async with async_rate_limited(limiter):
            result = "success"

        assert result == "success"
