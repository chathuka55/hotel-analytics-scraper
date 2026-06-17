"""Proxy rotation and management utilities."""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, List, Optional


class ProxyStatus(Enum):
    """Status of a proxy server."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    BANNED = "banned"


@dataclass
class Proxy:
    """Represents a proxy server configuration."""

    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    status: ProxyStatus = ProxyStatus.HEALTHY
    fail_count: int = 0
    last_used: Optional[float] = None
    success_count: int = 0
    response_times: List[float] = field(default_factory=list)

    @property
    def formatted_url(self) -> str:
        """Get formatted proxy URL with auth if present."""
        if self.username and self.password:
            # Insert credentials into URL
            proto = self.url.split("://")[0]
            host = "://".join(self.url.split("://")[1:])
            return f"{proto}://{self.username}:{self.password}@{host}"
        return self.url

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def record_success(self, response_time: float) -> None:
        """Record a successful request."""
        self.success_count += 1
        self.fail_count = 0
        self.response_times.append(response_time)
        # Keep only last 10 response times
        self.response_times = self.response_times[-10:]
        if self.status == ProxyStatus.FAILED and self.success_count > 3:
            self.status = ProxyStatus.HEALTHY

    def record_failure(self) -> None:
        """Record a failed request."""
        self.fail_count += 1
        if self.fail_count >= 5:
            self.status = ProxyStatus.BANNED
        elif self.fail_count >= 3:
            self.status = ProxyStatus.FAILED
        elif self.fail_count >= 1:
            self.status = ProxyStatus.DEGRADED

    def can_use(self) -> bool:
        """Check if proxy is usable."""
        return self.status in (ProxyStatus.HEALTHY, ProxyStatus.DEGRADED)

    def cooldown_remaining(self) -> float:
        """Get remaining cooldown time for failed proxies."""
        if self.status not in (ProxyStatus.FAILED, ProxyStatus.BANNED):
            return 0.0
        cooldown = 300 if self.status == ProxyStatus.FAILED else 1800
        if self.last_used is None:
            return 0.0
        elapsed = time.time() - self.last_used
        return max(0, cooldown - elapsed)

    def __repr__(self) -> str:
        return f"Proxy({self.url}, status={self.status.value})"


class ProxyRotator:
    """Rotates through a pool of proxy servers."""

    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        strategy: str = "round_robin",
    ):
        """Initialize proxy rotator.

        Args:
            proxy_list: List of proxy URLs
            username: Optional proxy auth username
            password: Optional proxy auth password
            strategy: Rotation strategy (round_robin, random, weighted, least_used)
        """
        self._strategy = strategy
        self._current_index = 0
        self._proxies: List[Proxy] = []
        self._username = username
        self._password = password

        if proxy_list:
            for url in proxy_list:
                self.add_proxy(url, username, password)

    @property
    def has_proxies(self) -> bool:
        """Check if any proxies are configured."""
        return len(self._proxies) > 0

    @property
    def healthy_count(self) -> int:
        """Count healthy proxies."""
        return sum(1 for p in self._proxies if p.status == ProxyStatus.HEALTHY)

    def add_proxy(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Add a proxy to the pool."""
        proxy = Proxy(
            url=url,
            username=username or self._username,
            password=password or self._password,
        )
        self._proxies.append(proxy)

    def get_proxy(self) -> Optional[Proxy]:
        """Get next proxy based on rotation strategy.

        Returns:
            Proxy instance or None if no healthy proxies
        """
        usable = [p for p in self._proxies if p.can_use()]
        if not usable:
            return None

        if self._strategy == "round_robin":
            proxy = usable[self._current_index % len(usable)]
            self._current_index += 1
        elif self._strategy == "random":
            proxy = random.choice(usable)
        elif self._strategy == "weighted":
            # Weight by health - fewer failures = higher weight
            weights = []
            for p in usable:
                if p.status == ProxyStatus.HEALTHY:
                    weights.append(3)
                else:
                    weights.append(1)
            proxy = random.choices(usable, weights=weights, k=1)[0]
        elif self._strategy == "least_used":
            proxy = min(usable, key=lambda p: p.last_used or 0)
        else:
            proxy = usable[0]

        proxy.last_used = time.time()
        return proxy

    def get_proxy_dict(self) -> Optional[dict]:
        """Get proxy as requests-compatible dictionary.

        Returns:
            Dict with http/https keys or None
        """
        proxy = self.get_proxy()
        if not proxy:
            return None
        url = proxy.formatted_url
        return {"http": url, "https": url}

    def record_proxy_success(self, proxy_url: str, response_time: float) -> None:
        """Record a successful request through a proxy."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.record_success(response_time)
                return

    def record_proxy_failure(self, proxy_url: str) -> None:
        """Record a failed request through a proxy."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.record_failure()
                return

    def get_stats(self) -> dict:
        """Get proxy pool statistics."""
        total = len(self._proxies)
        if total == 0:
            return {"total": 0, "message": "No proxies configured"}

        by_status = {}
        for p in self._proxies:
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1

        return {
            "total": total,
            "healthy": by_status.get("healthy", 0),
            "degraded": by_status.get("degraded", 0),
            "failed": by_status.get("failed", 0),
            "banned": by_status.get("banned", 0),
            "by_status": by_status,
            "avg_response_time": round(
                sum(p.avg_response_time for p in self._proxies) / total, 2
            ),
        }

    def __iter__(self) -> Iterator[Proxy]:
        """Iterate over all proxies."""
        return iter(self._proxies)

    def __len__(self) -> int:
        """Number of proxies."""
        return len(self._proxies)

    def __repr__(self) -> str:
        return f"ProxyRotator({len(self._proxies)} proxies, {self.healthy_count} healthy)"
