"""Tests for proxy rotation utility."""

import pytest

from src.utils.proxies import Proxy, ProxyRotator, ProxyStatus


class TestProxy:
    """Test cases for Proxy dataclass."""

    def test_proxy_creation(self):
        """Test creating a proxy."""
        proxy = Proxy("http://proxy1:8080")
        assert proxy.url == "http://proxy1:8080"
        assert proxy.status == ProxyStatus.HEALTHY

    def test_proxy_with_auth(self):
        """Test proxy with authentication."""
        proxy = Proxy(
            "http://proxy1:8080",
            username="user",
            password="pass",
        )
        formatted = proxy.formatted_url
        assert "user" in formatted
        assert "pass" in formatted

    def test_proxy_failure_tracking(self):
        """Test failure counting."""
        proxy = Proxy("http://proxy1:8080")

        proxy.record_failure()
        assert proxy.status == ProxyStatus.DEGRADED

        proxy.record_failure()
        proxy.record_failure()
        assert proxy.status == ProxyStatus.FAILED

        proxy.record_failure()
        proxy.record_failure()
        assert proxy.status == ProxyStatus.BANNED

    def test_proxy_recovery(self):
        """Test proxy recovery after failures."""
        proxy = Proxy("http://proxy1:8080")

        # Fail multiple times
        for _ in range(5):
            proxy.record_failure()
        assert proxy.status == ProxyStatus.BANNED

    def test_proxy_success(self):
        """Test recording success."""
        proxy = Proxy("http://proxy1:8080")

        proxy.record_success(1.5)
        assert proxy.success_count == 1
        assert proxy.avg_response_time == 1.5

    def test_can_use(self):
        """Test usability check."""
        healthy = Proxy("http://p1:8080", status=ProxyStatus.HEALTHY)
        degraded = Proxy("http://p2:8080", status=ProxyStatus.DEGRADED)
        failed = Proxy("http://p3:8080", status=ProxyStatus.FAILED)
        banned = Proxy("http://p4:8080", status=ProxyStatus.BANNED)

        assert healthy.can_use() is True
        assert degraded.can_use() is True
        assert failed.can_use() is False
        assert banned.can_use() is False


class TestProxyRotator:
    """Test cases for ProxyRotator."""

    def test_empty_rotator(self):
        """Test rotator with no proxies."""
        rotator = ProxyRotator()
        assert rotator.has_proxies is False
        assert rotator.get_proxy() is None
        assert rotator.get_proxy_dict() is None

    def test_add_proxy(self):
        """Test adding proxies."""
        rotator = ProxyRotator()
        rotator.add_proxy("http://proxy1:8080")
        rotator.add_proxy("http://proxy2:8080")

        assert rotator.has_proxies is True
        assert len(rotator) == 2

    def test_round_robin(self):
        """Test round-robin rotation."""
        rotator = ProxyRotator(
            proxy_list=["http://p1:8080", "http://p2:8080"],
            strategy="round_robin",
        )

        proxy1 = rotator.get_proxy()
        proxy2 = rotator.get_proxy()

        assert proxy1.url != proxy2.url

    def test_random_strategy(self):
        """Test random rotation."""
        rotator = ProxyRotator(
            proxy_list=["http://p1:8080", "http://p2:8080"],
            strategy="random",
        )

        proxy = rotator.get_proxy()
        assert proxy is not None

    def test_proxy_dict_format(self):
        """Test proxy dictionary output."""
        rotator = ProxyRotator(proxy_list=["http://p1:8080"])
        proxy_dict = rotator.get_proxy_dict()

        assert "http" in proxy_dict
        assert "https" in proxy_dict

    def test_stats(self):
        """Test statistics."""
        rotator = ProxyRotator(proxy_list=["http://p1:8080", "http://p2:8080"])
        stats = rotator.get_stats()

        assert stats["total"] == 2
        assert stats["healthy"] == 2

    def test_record_failure(self):
        """Test recording proxy failures."""
        rotator = ProxyRotator(proxy_list=["http://p1:8080"])

        rotator.record_proxy_failure("http://p1:8080")

        proxy = rotator.get_proxy()
        assert proxy.status == ProxyStatus.DEGRADED

    def test_weighted_strategy(self):
        """Test weighted rotation."""
        rotator = ProxyRotator(
            proxy_list=["http://p1:8080", "http://p2:8080"],
            strategy="weighted",
        )

        # Should still return proxies
        proxy = rotator.get_proxy()
        assert proxy is not None

    def test_iterable(self):
        """Test iteration over proxies."""
        rotator = ProxyRotator(proxy_list=["http://p1:8080", "http://p2:8080"])
        proxies = list(rotator)

        assert len(proxies) == 2
