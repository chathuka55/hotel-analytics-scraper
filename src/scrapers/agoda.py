"""Agoda.com scraper implementation."""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from src.config.settings import get_settings
from src.scrapers.travel import TravelSiteScraper
from src.storage.base import BaseStorage
from src.utils.city_ids import AGODA_CITY_IDS, lookup_city_id
from src.utils.proxies import ProxyRotator


class AgodaScraper(TravelSiteScraper):
    """Scraper for Agoda.com hotel data."""

    playwright_default = True
    page_size = 25

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
        offset: int = 0,
        **kwargs,
    ) -> str:
        date_fmt = "%Y-%m-%d"
        page = (offset // self.page_size) + 1
        params: Dict[str, Any] = {
            "checkIn": checkin_date.strftime(date_fmt),
            "checkOut": checkout_date.strftime(date_fmt),
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "page": page,
        }

        city_id = self.get_city_id(city)
        if city_id:
            params["cityId"] = city_id
        else:
            params["city"] = city

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/search?{query}"

    def enrich_results(
        self,
        results: List[Dict[str, Any]],
        city: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Fill missing prices via Agoda API when HTML parse is sparse."""
        if results and all(r.get("nightly_rate") for r in results):
            return results

        city_id = self.get_city_id(city)
        if not city_id:
            return results

        api_rows = self.scrape_api_fallback(city_id, checkin_date, checkout_date)
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
                if extra.get("city"):
                    row["city"] = extra["city"]
        return results

    def scrape_api_fallback(
        self,
        city_id: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        """Use Agoda's internal API when HTML scraping is incomplete."""
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
                return self._parse_api_response(response.json())
        except Exception as e:
            self.logger.debug(f"Agoda API fallback failed: {e}")
        return []

    def _parse_api_response(self, data: Dict) -> List[Dict[str, Any]]:
        results = []
        properties = data.get("results", {}).get("hotelResults", [])
        for prop in properties:
            try:
                from src.utils.location import normalize_city

                hotel = {
                    "source": "agoda",
                    "hotel_name": prop.get("hotelName", ""),
                    "city": normalize_city(prop.get("cityName", "")),
                    "country": prop.get("countryName", "Sri Lanka"),
                    "guest_score": prop.get("reviewScore", 0) / 10,
                    "review_count": prop.get("reviewCount", 0),
                    "nightly_rate": prop.get("priceDetail", {}).get(
                        "displayPrice", 0
                    ),
                    "currency": prop.get("priceDetail", {}).get(
                        "currency", "USD"
                    ),
                    "url": f"{self.base_url}{prop.get('hotelUrl', '')}",
                    "address": prop.get("address", ""),
                }
                if hotel["address"]:
                    from src.utils.location import extract_city_from_location

                    parsed = extract_city_from_location(
                        hotel["address"], hotel["city"]
                    )
                    if parsed:
                        hotel["city"] = parsed
                results.append(hotel)
            except Exception as e:
                self.logger.debug(f"Failed to parse Agoda API property: {e}")
        return results

    def get_city_id(self, city_name: str) -> Optional[str]:
        return lookup_city_id(AGODA_CITY_IDS, city_name)
