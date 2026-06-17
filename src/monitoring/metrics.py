"""Prometheus metrics collection for monitoring scraper health."""

import time
from functools import lru_cache, wraps
from typing import Any, Callable, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    start_http_server,
)

from src.config.settings import get_settings

# --- Metric Definitions ---

# Scrape counters
SCRAPES_TOTAL = Counter(
    "scraper_requests_total",
    "Total HTTP requests made",
    ["source", "status", "method"],
)

SCRAPE_ERRORS = Counter(
    "scraper_errors_total",
    "Total scraping errors",
    ["source", "error_type"],
)

HOTELS_SCRAPED = Counter(
    "scraper_hotels_total",
    "Total hotels scraped",
    ["source", "city"],
)

# Timing histograms
REQUEST_DURATION = Histogram(
    "scraper_request_duration_seconds",
    "HTTP request duration",
    ["source", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

PARSE_DURATION = Histogram(
    "scraper_parse_duration_seconds",
    "HTML parsing duration",
    ["source"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Gauges (current values)
ACTIVE_REQUESTS = Gauge(
    "scraper_active_requests",
    "Number of active requests",
    ["source"],
)

PROXY_FAILURES = Gauge(
    "scraper_proxy_failures",
    "Current proxy failure count",
    ["proxy"],
)

RATE_LIMIT_DELAY = Gauge(
    "scraper_rate_limit_delay_seconds",
    "Current rate limit delay",
)

# Application info
APP_INFO = Info("scraper_app", "Application information")


class MetricsCollector:
    """Centralized metrics collection for the scraper."""

    def __init__(self):
        self._server_started = False
        self._record_app_info()

    def _record_app_info(self) -> None:
        """Record application version info."""
        APP_INFO.info({"version": "1.0.0", "language": "python"})

    def start_server(self, port: Optional[int] = None) -> None:
        """Start the Prometheus metrics HTTP server.

        Args:
            port: Port to serve metrics on (default from settings)
        """
        if self._server_started:
            return

        settings = get_settings()
        if not settings.monitoring.enable_prometheus:
            return

        metrics_port = port or settings.monitoring.metrics_port
        start_http_server(metrics_port)
        self._server_started = True

    # --- Request Tracking ---

    def record_request(
        self,
        source: str,
        status: str = "success",
        method: str = "GET",
    ) -> None:
        """Record an HTTP request."""
        SCRAPES_TOTAL.labels(source=source, status=status, method=method).inc()

    def record_error(self, source: str, error_type: str = "unknown") -> None:
        """Record a scraping error."""
        SCRAPE_ERRORS.labels(source=source, error_type=error_type).inc()

    def record_hotel_scraped(self, source: str, city: str = "unknown") -> None:
        """Record a successfully scraped hotel."""
        HOTELS_SCRAPED.labels(source=source, city=city).inc()

    # --- Timing Context Managers ---

    def track_request_time(self, source: str, endpoint: str = "/"):
        """Context manager to track request duration."""
        return _RequestTimer(source, endpoint)

    def track_parse_time(self, source: str):
        """Context manager to track parsing duration."""
        return _ParseTimer(source)

    # --- Active Request Tracking ---

    def inc_active_requests(self, source: str) -> None:
        """Increment active request counter."""
        ACTIVE_REQUESTS.labels(source=source).inc()

    def dec_active_requests(self, source: str) -> None:
        """Decrement active request counter."""
        ACTIVE_REQUESTS.labels(source=source).dec()

    # --- Proxy Tracking ---

    def record_proxy_failure(self, proxy: str) -> None:
        """Record a proxy failure."""
        PROXY_FAILURES.labels(proxy=proxy).inc()

    def set_rate_limit_delay(self, delay_seconds: float) -> None:
        """Set current rate limit delay."""
        RATE_LIMIT_DELAY.set(delay_seconds)


class _RequestTimer:
    """Context manager for timing requests."""

    def __init__(self, source: str, endpoint: str):
        self.source = source
        self.endpoint = endpoint
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            REQUEST_DURATION.labels(
                source=self.source, endpoint=self.endpoint
            ).observe(duration)


class _ParseTimer:
    """Context manager for timing parsing operations."""

    def __init__(self, source: str):
        self.source = source
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            PARSE_DURATION.labels(source=self.source).observe(duration)


# --- Decorator Helpers ---

def track_duration(metric_histogram, **labels):
    """Decorator to track function execution duration."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metric_histogram.labels(**labels).observe(duration)
        return wrapper
    return decorator


# --- Singleton ---

@lru_cache()
def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return MetricsCollector()
