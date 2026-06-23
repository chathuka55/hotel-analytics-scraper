"""Abstract base scraper with common functionality."""

import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.monitoring.metrics import get_metrics
from src.parsers.hotel_parser import HotelParser
from src.storage.base import BaseStorage
from src.storage.csv_storage import CSVStorage
from src.utils.proxies import ProxyRotator
from src.utils.rate_limiter import RateLimiter
from src.utils.retry import with_retry
from src.utils.session import SessionManager

logger = get_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all hotel scrapers.

    Provides common functionality including:
    - HTTP session management
    - Rate limiting
    - Retry logic
    - Proxy rotation
    - Metrics collection
    - Storage integration
    """

    def __init__(
        self,
        source: str,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        """Initialize the scraper.

        Args:
            source: Source identifier (booking, agoda, etc.)
            storage: Storage backend for saving data
            proxy_rotator: Optional proxy rotation
        """
        self.source = source
        self.settings = get_settings()
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.metrics = get_metrics()

        # Initialize components
        self.session_manager = SessionManager(
            proxy_rotator=proxy_rotator,
            use_random_ua=True,
            max_retries=self.settings.scraping.max_retries,
        )

        self.rate_limiter = RateLimiter(
            requests_per_second=self.settings.scraping.rate_limit_per_second,
            min_delay=1.0,
            max_delay=10.0,
        )

        self.parser = HotelParser(source)
        self.storage = storage or CSVStorage()

        # State
        self._request_count = 0
        self._hotel_count = 0
        self._error_count = 0
        self._start_time: Optional[datetime] = None

        # Subclasses override this with their source-specific base URL.
        self.base_url: str = self.settings.get_source_url(self.source)

    @abstractmethod
    def build_search_url(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        **kwargs,
    ) -> str:
        """Build the search URL for the source.

        Args:
            city: City to search
            checkin_date: Check-in date
            checkout_date: Check-out date
            **kwargs: Additional source-specific parameters

        Returns:
            Full search URL
        """
        pass

    @abstractmethod
    def scrape(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Run the scraper and return results.

        Args:
            city: City to search
            checkin_date: Check-in date
            checkout_date: Check-out date
            **kwargs: Additional parameters

        Returns:
            List of scraped hotel records
        """
        pass

    @with_retry(max_retries=3, base_delay=2)
    def fetch_page(self, url: str, **kwargs) -> str:
        """Fetch a page with rate limiting and retry.

        Args:
            url: URL to fetch
            **kwargs: Additional requests parameters

        Returns:
            HTML content as string
        """
        # Rate limit
        self.rate_limiter.acquire()

        self.metrics.inc_active_requests(self.source)
        self.logger.debug(f"Fetching: {url}")

        try:
            with self.metrics.track_request_time(self.source, url):
                response = self.session_manager.get(url, **kwargs)

            self._request_count += 1

            if response.status_code == 200:
                self.metrics.record_request(self.source, "success")
                self.rate_limiter.record_success()
                return response.text
            elif response.status_code == 429:
                self.metrics.record_request(self.source, "rate_limited")
                self.metrics.record_error(self.source, "rate_limited")
                self.rate_limiter.record_error()
                self.logger.warning(f"Rate limited on {url}")
                raise Exception(f"Rate limited (429) on {url}")
            else:
                self.metrics.record_request(self.source, "error")
                self.logger.warning(
                    f"HTTP {response.status_code} for {url}"
                )
                raise Exception(
                    f"HTTP {response.status_code} for {url}"
                )

        except Exception:
            self._error_count += 1
            self.metrics.record_error(self.source, "request_failed")
            raise

        finally:
            self.metrics.dec_active_requests(self.source)

    def fetch_page_playwright(
        self, url: str, wait_for: Optional[str] = None, timeout: int = 30000
    ) -> str:
        """Fetch page using Playwright for JavaScript-rendered content.

        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for
            timeout: Page load timeout in ms

        Returns:
            HTML content after JavaScript execution
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.logger.error("Playwright not installed. Run: playwright install")
            raise

        self.rate_limiter.acquire()
        self.metrics.inc_active_requests(self.source)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.settings.playwright.headless,
                    slow_mo=self.settings.playwright.slow_mo,
                )
                context = browser.new_context(
                    user_agent=self.session_manager.session.headers.get(
                        "User-Agent", ""
                    ),
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                with self.metrics.track_request_time(self.source, url):
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)

                    if wait_for:
                        page.wait_for_selector(wait_for, timeout=timeout)

                    # Additional wait for lazy-loaded content
                    page.wait_for_timeout(2000)

                    html = page.content()

                context.close()
                browser.close()

            self._request_count += 1
            self.metrics.record_request(self.source, "success")
            return html

        except Exception as e:
            self._error_count += 1
            self.metrics.record_error(self.source, "playwright_failed")
            self.logger.error(f"Playwright fetch failed: {e}")
            raise

        finally:
            self.metrics.dec_active_requests(self.source)

    def parse_results(
        self, html: str, city: str, checkin_date: date, checkout_date: date
    ) -> List[Dict[str, Any]]:
        """Parse search results HTML.

        Args:
            html: HTML content
            city: City name
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            List of parsed hotel data
        """
        with self.metrics.track_parse_time(self.source):
            results = self.parser.parse_search_results(
                html, city, checkin_date, checkout_date
            )

        self._hotel_count += len(results)
        self.logger.info(f"Parsed {len(results)} hotels from {self.source}")
        return results

    def save_results(self, records: List[Dict[str, Any]]) -> int:
        """Save records to storage.

        Args:
            records: List of hotel records

        Returns:
            Number of records saved
        """
        if not records:
            return 0

        # Validate before saving
        validation = self.parser.validate_batch(records)
        if not validation.is_valid:
            self.logger.warning(
                f"Validation issues: {len(validation.errors)} errors"
            )

        saved = self.storage.save(records)
        self.logger.info(f"Saved {saved} records to storage")
        return saved

    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics.

        Returns:
            Dictionary with stats
        """
        duration = 0.0
        if self._start_time:
            duration = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "source": self.source,
            "requests": self._request_count,
            "hotels": self._hotel_count,
            "errors": self._error_count,
            "duration_seconds": round(duration, 2),
            "rate_limit": self.rate_limiter.get_stats(),
        }

    def reset_stats(self) -> None:
        """Reset scraping statistics."""
        self._request_count = 0
        self._hotel_count = 0
        self._error_count = 0
        self._start_time = None

    def close(self) -> None:
        """Clean up resources."""
        self.session_manager.close()
        self.storage.close()

    def __enter__(self):
        self._start_time = datetime.utcnow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(source={self.source})"
