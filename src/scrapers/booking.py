"""Booking.com scraper implementation."""

import time
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.scrapers.base import BaseScraper
from src.storage.base import BaseStorage
from src.utils.proxies import ProxyRotator

logger = get_logger(__name__)


class BookingScraper(BaseScraper):
    """Scraper for Booking.com hotel data.

    Handles both static HTML and JavaScript-rendered content.
    Uses Playwright for pages that require browser automation.
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("booking", storage, proxy_rotator)
        self.base_url = get_settings().sources.booking_base_url

    def build_search_url(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        offset: int = 0,
    ) -> str:
        """Build Booking.com search URL.

        Args:
            city: Destination city
            checkin_date: Check-in date
            checkout_date: Check-out date
            adults: Number of adults
            children: Number of children
            rooms: Number of rooms
            offset: Pagination offset

        Returns:
            Complete search URL
        """
        date_fmt = "%Y-%m-%d"
        params = {
            "ss": city,
            "checkin": checkin_date.strftime(date_fmt),
            "checkout": checkout_date.strftime(date_fmt),
            "group_adults": adults,
            "group_children": children,
            "no_rooms": rooms,
            "offset": offset,
        }

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/searchresults.html?{query}"

    def scrape(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        max_pages: int = 5,
        use_playwright: bool = False,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape Booking.com for hotel data.

        Args:
            city: City to search
            checkin_date: Check-in date
            checkout_date: Check-out date
            max_pages: Maximum pages to scrape
            use_playwright: Use browser automation
            **kwargs: Additional parameters

        Returns:
            List of hotel records
        """
        all_results = []
        offset = 0

        self.logger.info(
            f"Starting Booking.com scrape: {city}, "
            f"{checkin_date} to {checkout_date}"
        )

        for page in range(max_pages):
            self.logger.info(f"Fetching page {page + 1}/{max_pages}")

            url = self.build_search_url(
                city, checkin_date, checkout_date, offset=offset
            )

            try:
                if use_playwright:
                    html = self.fetch_page_playwright(
                        url, wait_for="[data-testid='property-card']"
                    )
                else:
                    html = self.fetch_page(url)

                results = self.parse_results(
                    html, city, checkin_date, checkout_date
                )

                if not results:
                    self.logger.info("No more results found")
                    break

                all_results.extend(results)
                self.logger.info(
                    f"Page {page + 1}: Found {len(results)} hotels"
                )

                # Check for next page
                if not self._has_next_page(html):
                    break

                offset += 25  # Booking.com uses 25 results per page

                # Rate limiting between pages
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error on page {page + 1}: {e}")
                if not use_playwright:
                    self.logger.info("Retrying with Playwright...")
                    try:
                        html = self.fetch_page_playwright(
                            url, wait_for="[data-testid='property-card']"
                        )
                        results = self.parse_results(
                            html, city, checkin_date, checkout_date
                        )
                        all_results.extend(results)
                    except Exception as e2:
                        self.logger.error(f"Playwright retry failed: {e2}")
                break

        if all_results:
            self.save_results(all_results)

        self.logger.info(
            f"Booking.com scrape complete: {len(all_results)} hotels"
        )
        return all_results

    def scrape_with_monthly_dates(
        self,
        city: str,
        year: int,
        month: int,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """Scrape for a specific month to analyze check-in patterns.

        Args:
            city: City to search
            year: Year to analyze
            month: Month to analyze (1-12)
            max_pages: Max pages per date combination

        Returns:
            All hotel records for the month
        """
        from calendar import monthrange

        _, last_day = monthrange(year, month)
        all_results = []

        # Scrape for each day of the month as check-in date
        # Using 1-day stays to get daily check-in data
        for day in range(1, min(last_day + 1, 8)):  # Sample first week for efficiency
            checkin = date(year, month, day)
            checkout = date(year, month, min(day + 1, last_day))

            self.logger.info(f"Scraping check-in date: {checkin}")

            try:
                results = self.scrape(
                    city=city,
                    checkin_date=checkin,
                    checkout_date=checkout,
                    max_pages=max_pages,
                )
                all_results.extend(results)

                # Rate limiting between dates
                time.sleep(3)

            except Exception as e:
                self.logger.error(f"Error scraping {checkin}: {e}")
                continue

        return all_results

    def _has_next_page(self, html: str) -> bool:
        """Check if there's a next page in search results.

        Args:
            html: HTML content

        Returns:
            True if next page exists
        """
        soup = BeautifulSoup(html, "lxml")
        next_btn = soup.select_one("button[aria-label='Next page']")
        if next_btn and next_btn.get("disabled"):
            return False
        return bool(next_btn)

    def get_popular_cities_sri_lanka(self) -> List[str]:
        """Get list of popular Sri Lankan cities to scrape.

        Returns:
            List of city names
        """
        return [
            "Colombo",
            "Kandy",
            "Galle",
            "Negombo",
            "Nuwara Eliya",
            "Bentota",
            "Sigiriya",
            "Ella",
            "Mirissa",
            "Trincomalee",
            "Jaffna",
            "Anuradhapura",
            "Dambulla",
            "Hikkaduwa",
            "Unawatuna",
        ]
