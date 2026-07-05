"""Expedia.com scraper implementation."""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from src.config.settings import get_settings
from src.scrapers.travel import TravelSiteScraper
from src.storage.base import BaseStorage
from src.utils.city_ids import EXPEDIA_REGION_IDS, lookup_city_id
from src.utils.proxies import ProxyRotator


class ExpediaScraper(TravelSiteScraper):
    """Scraper for Expedia.com hotel data."""

    playwright_default = True
    page_size = 25

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
        offset: int = 0,
        **kwargs,
    ) -> str:
        date_fmt = "%Y-%m-%d"
        destination = quote_plus(f"{city}, Sri Lanka")
        region_id = self.get_region_id(city)

        params = {
            "startDate": checkin_date.strftime(date_fmt),
            "endDate": checkout_date.strftime(date_fmt),
            "adults": adults,
            "startIndex": offset,
        }
        if region_id:
            params["regionId"] = region_id
        else:
            params["destination"] = destination

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/Hotel-Search?{query}"

    def enrich_results(
        self,
        results: List[Dict[str, Any]],
        city: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Backfill from GraphQL when HTML results lack pricing."""
        if results and all(r.get("nightly_rate") for r in results):
            return results

        region_id = self.get_region_id(city)
        if not region_id:
            return results

        api_rows = self.scrape_graphql_api(
            region_id, checkin_date, checkout_date
        )
        if not api_rows:
            return results

        api_by_name = {
            (r.get("hotel_name") or "").lower(): r for r in api_rows
        }
        for row in results:
            key = (row.get("hotel_name") or "").lower()
            if key in api_by_name:
                extra = api_by_name[key]
                row.setdefault("nightly_rate", extra.get("nightly_rate", 0))
                row.setdefault("currency", extra.get("currency", "USD"))
                row.setdefault("guest_score", extra.get("guest_score", 0))
                row.setdefault("review_count", extra.get("review_count", 0))
        return results

    def scrape_graphql_api(
        self,
        region_id: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
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
            "query": (
                "query PropertySearch($context: ContextInput, $criteria: CriteriaInput, "
                "$resultsStartingIndex: Int, $resultsSize: Int) { propertySearch(context: $context, "
                "criteria: $criteria, resultsStartingIndex: $resultsStartingIndex, "
                "resultsSize: $resultsSize) { properties { propertyId name price { lead { amount } } "
                "reviews { score total } } } }"
            ),
        }

        try:
            response = self.session_manager.post(
                api_url,
                json=query,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                return self._parse_graphql_response(response.json())
        except Exception as e:
            self.logger.debug(f"Expedia GraphQL fallback failed: {e}")
        return []

    def _parse_graphql_response(self, data: Dict) -> List[Dict[str, Any]]:
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
                results.append(
                    {
                        "source": "expedia",
                        "hotel_name": prop.get("name", ""),
                        "guest_score": reviews.get("score", 0),
                        "review_count": reviews.get("total", 0),
                        "nightly_rate": price.get("amount", 0),
                        "currency": "USD",
                    }
                )
            except Exception as e:
                self.logger.debug(f"Failed to parse Expedia property: {e}")
        return results

    def get_region_id(self, city: str) -> Optional[str]:
        return lookup_city_id(EXPEDIA_REGION_IDS, city)
