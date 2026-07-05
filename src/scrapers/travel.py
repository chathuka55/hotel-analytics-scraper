"""Advanced base scraper for travel/hotel booking sites."""

import time
from abc import abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings
from src.scrapers.base import BaseScraper
from src.storage.base import BaseStorage
from src.utils.location import SRI_LANKAN_CITIES
from src.utils.proxies import ProxyRotator
from src.utils.validators import filter_scraped_records


class TravelSiteScraper(BaseScraper):
    """Shared scraping logic for OTA / metasearch hotel sites.

    Features:
    - Playwright with automatic HTTP fallback retry
    - Configurable pagination and rate limiting
    - Optional scroll-to-load for infinite-scroll result pages
    - Pre-save filtering of unknown/incomplete records
    - Location-aware city resolution via HotelParser
    """

    playwright_default: bool = True
    page_size: int = 25
    scroll_pages: bool = False

    def __init__(
        self,
        source: str,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__(source, storage, proxy_rotator)
        self.base_url = get_settings().get_source_url(source)

    @abstractmethod
    def build_search_url(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        **kwargs,
    ) -> str:
        pass

    def get_wait_selector(self) -> str:
        """CSS selector to wait for after page load."""
        return self.parser.selectors.get(self.source, "search_result_item") or ""

    def get_next_page_offset(self, page_index: int) -> Dict[str, Any]:
        """Return kwargs for the next page (offset, page number, etc.)."""
        return {"offset": page_index * self.page_size}

    def has_next_page(self, html: str) -> bool:
        """Return True if another results page exists."""
        next_sel = self.parser.selectors.get(self.source, "next_page_button")
        if not next_sel:
            return False
        soup = self.parser.parse_with_soup(html)
        next_btn = soup.select_one(next_sel)
        if next_btn and next_btn.get("disabled") is not None:
            return False
        if next_btn and "disabled" in (next_btn.get("class") or []):
            return False
        return bool(next_btn)

    def fetch_search_page(
        self, url: str, use_playwright: bool, wait_for: str
    ) -> str:
        """Fetch a search results page with Playwright or HTTP."""
        if use_playwright:
            return self.fetch_page_playwright(
                url, wait_for=wait_for or None, timeout=45000
            )
        return self.fetch_page(url)

    def fetch_with_playwright_retry(
        self, url: str, wait_for: str, use_playwright: bool
    ) -> str:
        """Try HTTP first when allowed, then fall back to Playwright."""
        try:
            return self.fetch_search_page(url, use_playwright, wait_for)
        except Exception as first_error:
            if use_playwright:
                raise first_error
            self.logger.info("Retrying with Playwright...")
            return self.fetch_page_playwright(
                url, wait_for=wait_for or None, timeout=45000
            )

    def enrich_results(
        self,
        results: List[Dict[str, Any]],
        city: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Hook for subclasses to enrich parsed rows (e.g. API fallback)."""
        return results

    def scrape(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        max_pages: int = 5,
        use_playwright: Optional[bool] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape hotel listings with pagination and quality filtering."""
        if use_playwright is None:
            use_playwright = self.playwright_default

        all_results: List[Dict[str, Any]] = []
        wait_for = self.get_wait_selector()

        self.logger.info(
            f"Starting {self.source} scrape: {city}, "
            f"{checkin_date} to {checkout_date}"
        )

        for page in range(max_pages):
            self.logger.info(f"Fetching page {page + 1}/{max_pages}")
            page_kwargs = self.get_next_page_offset(page)
            url = self.build_search_url(
                city, checkin_date, checkout_date, **page_kwargs
            )

            try:
                html = self.fetch_with_playwright_retry(
                    url, wait_for, use_playwright
                )
                results = self.parse_results(
                    html, city, checkin_date, checkout_date
                )
                results = self.enrich_results(
                    results, city, checkin_date, checkout_date
                )

                if not results:
                    self.logger.info("No more results found")
                    break

                all_results.extend(results)
                self.logger.info(
                    f"Page {page + 1}: Found {len(results)} hotels"
                )

                if not self.has_next_page(html):
                    break

                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error on page {page + 1}: {e}")
                break

        all_results = filter_scraped_records(all_results)
        if all_results:
            self.save_results(all_results)

        self.logger.info(
            f"{self.source} scrape complete: {len(all_results)} hotels"
        )
        return all_results

    def scrape_with_monthly_dates(
        self,
        city: str,
        year: int,
        month: int,
        max_pages: int = 3,
        use_playwright: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Sample first week of a month for check-in pattern analysis."""
        from calendar import monthrange

        _, last_day = monthrange(year, month)
        all_results: List[Dict[str, Any]] = []

        for day in range(1, min(last_day + 1, 8)):
            checkin = date(year, month, day)
            checkout = date(year, month, min(day + 1, last_day))
            self.logger.info(f"{self.source}: Scraping check-in {checkin}")

            try:
                results = self.scrape(
                    city=city,
                    checkin_date=checkin,
                    checkout_date=checkout,
                    max_pages=max_pages,
                    use_playwright=use_playwright,
                )
                all_results.extend(results)
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"{self.source} error on {checkin}: {e}")
                continue

        return all_results

    def save_results(self, records: List[Dict[str, Any]]) -> int:
        """Save only validated, non-junk records."""
        records = filter_scraped_records(records)
        return super().save_results(records)

    @staticmethod
    def get_popular_cities_sri_lanka() -> List[str]:
        return list(SRI_LANKAN_CITIES)
