"""Agoda.com scraper implementation."""

import json
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.scrapers.base import BaseScraper
from src.storage.base import BaseStorage
from src.utils.proxies import ProxyRotator

logger = get_logger(__name__)


class AgodaScraper(BaseScraper):
    """Scraper for Agoda.com hotel data.

    Agoda uses heavy JavaScript rendering, so Playwright
    is often required for reliable scraping.
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("agoda", storage, proxy_rotator)
        self.base_url = get_settings().sources.agoda_base_url

    def build_search_url(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        page: int = 1,
    ) -> str:
        """Build Agoda search URL.

        Args:
            city: Destination city
            checkin_date: Check-in date
            checkout_date: Check-out date
            adults: Number of adults
            children: Number of children
            rooms: Number of rooms
            page: Page number

        Returns:
            Complete search URL
        """
        date_fmt = "%Y-%m-%d"
        params = {
            "city": city,
            "checkIn": checkin_date.strftime(date_fmt),
            "checkOut": checkout_date.strftime(date_fmt),
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "page": page,
        }

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/search?{query}"

    def scrape(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        max_pages: int = 5,
        use_playwright: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape Agoda for hotel data.

        Args:
            city: City to search
            checkin_date: Check-in date
            checkout_date: Check-out date
            max_pages: Maximum pages to scrape
            use_playwright: Use browser (recommended for Agoda)
            **kwargs: Additional parameters

        Returns:
            List of hotel records
        """
        all_results = []

        self.logger.info(
            f"Starting Agoda scrape: {city}, "
            f"{checkin_date} to {checkout_date}"
        )

        for page in range(1, max_pages + 1):
            self.logger.info(f"Fetching page {page}/{max_pages}")

            url = self.build_search_url(
                city, checkin_date, checkout_date, page=page
            )

            try:
                if use_playwright:
                    html = self.fetch_page_playwright(
                        url, wait_for=".PropertyCard", timeout=45000
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
                self.logger.info(f"Page {page}: Found {len(results)} hotels")

                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error on page {page}: {e}")
                break

        if all_results:
            self.save_results(all_results)

        self.logger.info(f"Agoda scrape complete: {len(all_results)} hotels")
        return all_results

    def scrape_api_fallback(
        self,
        city_id: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Attempt to use Agoda's internal API for data.

        This requires capturing API calls from the browser.
        Useful when HTML scraping is blocked.

        Args:
            city_id: Agoda city ID
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            List of hotel records
        """
        api_url = f"{self.base_url}/api/cronos/property/BatchSearch"

        payload = {
            "cityId": city_id,
            "checkIn": checkin_date.strftime("%Y-%m-%d"),
            "checkOut": checkout_date.strftime("%Y-%m-%d"),
            "rooms": [{"adults": 2, "children": []}],
            "page": 1,
            "pageSize": 25,
        }

        try:
            response = self.session_manager.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_api_response(data)
            else:
                logger.warning(f"API returned {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"API fallback failed: {e}")
            return []

    def _parse_api_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse Agoda API response.

        Args:
            data: API response JSON

        Returns:
            List of hotel records
        """
        results = []

        properties = data.get("results", {}).get("hotelResults", [])
        for prop in properties:
            try:
                hotel = {
                    "source": "agoda",
                    "hotel_name": prop.get("hotelName", ""),
                    "city": prop.get("cityName", ""),
                    "country": prop.get("countryName", "Sri Lanka"),
                    "guest_score": prop.get("reviewScore", 0) / 10,
                    "review_count": prop.get("reviewCount", 0),
                    "nightly_rate": prop.get("priceDetail", {})
                    .get("displayPrice", 0),
                    "currency": prop.get("priceDetail", {})
                    .get("currency", "USD"),
                    "url": f"{self.base_url}{prop.get('hotelUrl', '')}",
                }
                results.append(hotel)
            except Exception as e:
                logger.debug(f"Failed to parse API property: {e}")
                continue

        return results

    def get_city_id(self, city_name: str) -> Optional[str]:
        """Get Agoda city ID from city name.

        Args:
            city_name: City name

        Returns:
            City ID string or None
        """
        # Common Sri Lankan city IDs
        city_ids = {
            "colombo": "14932",
            "kandy": "4919",
            "galle": "21674",
            "negombo": "13409",
            "nuwara eliya": "21676",
            "bentota": "14781",
            "sigiriya": "16056",
            "ella": "13418",
            "mirissa": "21354",
            "trincomalee": "14782",
            "jaffna": "13424",
            "anuradhapura": "16058",
            "dambulla": "13413",
            "hikkaduwa": "16060",
            "unawatuna": "14783",
        }

        city_key = city_name.lower().strip()
        return city_ids.get(city_key)

    def scrape_with_monthly_dates(
        self,
        city: str,
        year: int,
        month: int,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """Scrape Agoda for a specific month.

        Args:
            city: City name
            year: Year
            month: Month (1-12)
            max_pages: Max pages per scrape

        Returns:
            Combined results
        """
        from calendar import monthrange

        _, last_day = monthrange(year, month)
        all_results = []

        for day in range(1, min(last_day + 1, 8)):
            checkin = date(year, month, day)
            checkout = date(year, month, min(day + 1, last_day))

            self.logger.info(f"Agoda: Scraping check-in {checkin}")

            try:
                results = self.scrape(
                    city=city,
                    checkin_date=checkin,
                    checkout_date=checkout,
                    max_pages=max_pages,
                    use_playwright=True,
                )
                all_results.extend(results)
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"Agoda error on {checkin}: {e}")
                continue

        return all_results
