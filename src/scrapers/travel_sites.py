"""Scrapers for additional travel/hotel booking sites."""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from src.scrapers.travel import TravelSiteScraper
from src.storage.base import BaseStorage
from src.utils.city_ids import (
    EXPEDIA_REGION_IDS,
    TRIPADVISOR_GEO_IDS,
    TRIPCOM_CITY_IDS,
    lookup_city_id,
)
from src.utils.proxies import ProxyRotator


class ExpediaGroupMixin:
    """Shared region-ID URLs and GraphQL enrichment for Expedia Group sites."""

    region_ids: Dict[str, str] = EXPEDIA_REGION_IDS

    def get_region_id(self, city: str) -> Optional[str]:
        return lookup_city_id(self.region_ids, city)

    def enrich_results(
        self,
        results: List[Dict[str, Any]],
        city: str,
        checkin_date: date,
        checkout_date: date,
    ) -> List[Dict[str, Any]]:
        if results and all(r.get("nightly_rate") for r in results):
            return results

        region_id = self.get_region_id(city)
        if not region_id:
            return results

        from src.scrapers.expedia import ExpediaScraper

        helper = ExpediaScraper(storage=self.storage, proxy_rotator=None)
        helper.base_url = self.base_url
        api_rows = helper.scrape_graphql_api(region_id, checkin_date, checkout_date)
        if not api_rows:
            return results

        api_by_name = {(r.get("hotel_name") or "").lower(): r for r in api_rows}
        for row in results:
            key = (row.get("hotel_name") or "").lower()
            if key in api_by_name:
                extra = api_by_name[key]
                row.setdefault("nightly_rate", extra.get("nightly_rate", 0))
                row.setdefault("currency", extra.get("currency", "USD"))
                row.setdefault("guest_score", extra.get("guest_score", 0))
                row.setdefault("review_count", extra.get("review_count", 0))
        return results


class SkyscannerScraper(TravelSiteScraper):
    """Scraper for Skyscanner Hotels."""

    playwright_default = True
    page_size = 20

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("skyscanner", storage, proxy_rotator)

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
        dest = quote_plus(f"{city}, Sri Lanka")
        page = (offset // self.page_size) + 1
        return (
            f"{self.base_url}/hotels/search?"
            f"entityName={dest}&"
            f"checkin={checkin_date.strftime(date_fmt)}&"
            f"checkout={checkout_date.strftime(date_fmt)}&"
            f"adults={adults}&"
            f"page={page}"
        )


class RehlatScraper(TravelSiteScraper):
    """Scraper for Rehlat hotel search."""

    playwright_default = True
    page_size = 25

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("rehlat", storage, proxy_rotator)

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
        page = (offset // self.page_size) + 1
        return (
            f"{self.base_url}/en/hotels/search?"
            f"city={quote_plus(city)}&"
            f"country=Sri+Lanka&"
            f"checkIn={checkin_date.strftime(date_fmt)}&"
            f"checkOut={checkout_date.strftime(date_fmt)}&"
            f"rooms=1&adults={adults}&"
            f"page={page}"
        )


class TravelokaScraper(TravelSiteScraper):
    """Scraper for Traveloka hotels."""

    playwright_default = True
    page_size = 25

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("traveloka", storage, proxy_rotator)

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
        page = (offset // self.page_size) + 1
        return (
            f"{self.base_url}/en-en/hotel/search?"
            f"spec=1.{adults}.0.{checkin_date.strftime(date_fmt)}."
            f"{checkout_date.strftime(date_fmt)}&"
            f"query={quote_plus(city + ', Sri Lanka')}&"
            f"page={page}"
        )


class TripAdvisorScraper(TravelSiteScraper):
    """Scraper for TripAdvisor hotel listings."""

    playwright_default = True
    page_size = 30

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("tripadvisor", storage, proxy_rotator)

    def get_geo_id(self, city: str) -> str:
        return lookup_city_id(TRIPADVISOR_GEO_IDS, city) or "293962"

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
        geo = self.get_geo_id(city)
        slug = quote_plus(city.replace(" ", "_"))
        return (
            f"{self.base_url}/Hotels-g{geo}-{slug}_Sri_Lanka-Hotels.html?"
            f"checkIn={checkin_date.strftime(date_fmt)}&"
            f"checkOut={checkout_date.strftime(date_fmt)}&"
            f"adults={adults}&"
            f"offset={offset}"
        )


class TripComScraper(TravelSiteScraper):
    """Scraper for Trip.com hotels."""

    playwright_default = True
    page_size = 25

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("tripcom", storage, proxy_rotator)

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
        page = (offset // self.page_size) + 1
        city_id = lookup_city_id(TRIPCOM_CITY_IDS, city)
        city_param = f"cityId={city_id}" if city_id else f"city={quote_plus(city)}"
        return (
            f"{self.base_url}/hotels/list?"
            f"{city_param}&"
            f"countryId=110&"
            f"checkIn={checkin_date.strftime(date_fmt)}&"
            f"checkOut={checkout_date.strftime(date_fmt)}&"
            f"adult={adults}&"
            f"page={page}"
        )


class GoSeekScraper(TravelSiteScraper):
    """Scraper for GoSeek hotel search."""

    playwright_default = True
    page_size = 25

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("goseek", storage, proxy_rotator)

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
        page = (offset // self.page_size) + 1
        return (
            f"{self.base_url}/hotels?"
            f"destination={quote_plus(city + ', Sri Lanka')}&"
            f"checkin={checkin_date.strftime(date_fmt)}&"
            f"checkout={checkout_date.strftime(date_fmt)}&"
            f"rooms=1&adults={adults}&"
            f"page={page}"
        )


class EtripScraper(TravelSiteScraper):
    """Scraper for Etrip hotel metasearch."""

    playwright_default = True
    page_size = 20

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("etrip", storage, proxy_rotator)

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
        page = (offset // self.page_size) + 1
        return (
            f"{self.base_url}/hotels?"
            f"q={quote_plus(city + ', Sri Lanka')}&"
            f"checkin={checkin_date.strftime(date_fmt)}&"
            f"checkout={checkout_date.strftime(date_fmt)}&"
            f"guests={adults}&"
            f"page={page}"
        )


class HotelsComScraper(ExpediaGroupMixin, TravelSiteScraper):
    """Scraper for Hotels.com (Expedia Group)."""

    playwright_default = True
    page_size = 25

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("hotelscom", storage, proxy_rotator)

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
            params["destination"] = f"{city}, Sri Lanka"

        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/Hotel-Search?{query}"


TRAVEL_SCRAPER_CLASSES = {
    "skyscanner": SkyscannerScraper,
    "rehlat": RehlatScraper,
    "traveloka": TravelokaScraper,
    "tripadvisor": TripAdvisorScraper,
    "tripcom": TripComScraper,
    "goseek": GoSeekScraper,
    "etrip": EtripScraper,
    "hotelscom": HotelsComScraper,
}


def create_travel_scraper(
    source: str,
    storage: Optional[BaseStorage] = None,
    proxy_rotator: Optional[ProxyRotator] = None,
) -> TravelSiteScraper:
    """Factory for travel-site scrapers."""
    cls = TRAVEL_SCRAPER_CLASSES.get(source.lower())
    if not cls:
        raise ValueError(f"No travel scraper for source: {source}")
    return cls(storage=storage, proxy_rotator=proxy_rotator)
