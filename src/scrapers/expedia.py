"""Expedia.com scraper implementation."""

import json
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


class ExpediaScraper(BaseScraper):
    """Scraper for Expedia.com hotel data.

    Expedia also uses JavaScript rendering, so Playwright
    is recommended for consistent results.
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("expedia", storage, proxy_rotator)
        self.base_url = get_settings().sources.expedia_base_url

    def build_search_url(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        adults: int = 2,
        children: List[int] = None,
        start_index: int = 0,
    ) -> str:
        """Build Expedia search URL.

        Args:
            city: Destination city
            checkin_date: Check-in date
            checkout_date: Check-out date
            adults: Number of adults
            children: List of children ages
            start_index: Pagination start index

        Returns:
            Complete search URL
        """
        date_fmt = "%Y-%m-%d"

        # Expedia uses a path-based search
        destination = quote_plus(city)

        params = {
            "startDate": checkin_date.strftime(date_fmt),
            "endDate": checkout_date.strftime(date_fmt),
            "adults": adults,
            "startIndex": start_index,
        }

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return (
            f"{self.base_url}/Hotel-Search?"
            f"destination={destination}&{query}"
        )

    def scrape(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        max_pages: int = 5,
        use_playwright: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape Expedia for hotel data.

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
        start_index = 0

        self.logger.info(
            f"Starting Expedia scrape: {city}, "
            f"{checkin_date} to {checkout_date}"
        )

        for page in range(max_pages):
            self.logger.info(f"Fetching page {page + 1}/{max_pages}")

            url = self.build_search_url(
                city, checkin_date, checkout_date, start_index=start_index
            )

            try:
                if use_playwright:
                    html = self.fetch_page_playwright(
                        url,
                        wait_for=".uitk-card",
                        timeout=45000,
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

                start_index += 25
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error on page {page + 1}: {e}")
                break

        if all_results:
            self.save_results(all_results)

        self.logger.info(f"Expedia scrape complete: {len(all_results)} hotels")
        return all_results

    def scrape_graphql_api(
        self,
        region_id: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Use Expedia's GraphQL API for data extraction.

        More reliable than HTML scraping when available.

        Args:
            region_id: Expedia region/city ID
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            List of hotel records
        """
        api_url = f"{self.base_url}/graphql"

        query = {
            "operationName": "PropertySearch",
            "variables": {
                "context": {
                    "siteId": 1,
                    "locale": "en_US",
                    "currency": "USD",
                },
                "criteria": {
                    "primary": {
                        "dateRange": {
                            "checkInDate": {
                                "day": checkin_date.day,
                                "month": checkin_date.month,
                                "year": checkin_date.year,
                            },
                            "checkOutDate": {
                                "day": checkout_date.day,
                                "month": checkout_date.month,
                                "year": checkout_date.year,
                            },
                        },
                        "destination": {"regionId": region_id},
                        "rooms": [{"adults": 2}],
                    }
                },
                "resultsSize": 25,
                "resultsStartingIndex": 0,
            },
            "query": "query PropertySearch($context: ContextInput, $criteria: CriteriaInput, "
            "$resultsStartingIndex: Int, $resultsSize: Int) { propertySearch(context: $context, "
            "criteria: $criteria, resultsStartingIndex: $resultsStartingIndex, "
            "resultsSize: $resultsSize) { properties { propertyId name price { lead { amount } } "
            "reviews { score total } } } }",
        }

        try:
            response = self.session_manager.post(
                api_url,
                json=query,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_graphql_response(data)
            else:
                logger.warning(f"GraphQL API returned {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"GraphQL API failed: {e}")
            return []

    def _parse_graphql_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse GraphQL API response.

        Args:
            data: API response

        Returns:
            List of hotel records
        """
        results = []

        properties = (
            data.get("data", {})
            .get("propertySearch", {})
            .get("properties", [])
        )

        for prop in properties:
            try:
                reviews = prop.get("reviews", {})
                price = prop.get("price", {}).get("lead", {})

                hotel = {
                    "source": "expedia",
                    "hotel_name": prop.get("name", ""),
                    "guest_score": reviews.get("score", 0),
                    "review_count": reviews.get("total", 0),
                    "nightly_rate": price.get("amount", 0),
                    "currency": "USD",
                }
                results.append(hotel)
            except Exception as e:
                logger.debug(f"Failed to parse property: {e}")
                continue

        return results

    def get_region_id(self, city: str) -> Optional[str]:
        """Get Expedia region ID for a city.

        Args:
            city: City name

        Returns:
            Region ID or None
        """
        region_ids = {
            "colombo": "6056893",
            "kandy": "6057007",
            "galle": "6057123",
            "negombo": "6056894",
            "nuwara eliya": "6057124",
            "bentota": "6057125",
            "sigiriya": "6057008",
            "ella": "6057126",
            "mirissa": "6057127",
            "trincomalee": "6057128",
            "jaffna": "6057129",
            "anuradhapura": "6057009",
            "dambulla": "6057010",
            "hikkaduwa": "6057130",
            "unawatuna": "6057131",
        }

        return region_ids.get(city.lower().strip())

    def scrape_with_monthly_dates(
        self,
        city: str,
        year: int,
        month: int,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """Scrape Expedia for a specific month.

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

            self.logger.info(f"Expedia: Scraping check-in {checkin}")

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
                self.logger.error(f"Expedia error on {checkin}: {e}")
                continue

        return all_results
