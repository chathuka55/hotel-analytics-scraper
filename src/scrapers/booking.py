"""Booking.com scraper implementation."""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from src.config.settings import get_settings
from src.scrapers.travel import TravelSiteScraper
from src.storage.base import BaseStorage
from src.utils.proxies import ProxyRotator


class BookingScraper(TravelSiteScraper):
    """Scraper for Booking.com hotel data."""

    playwright_default = False
    page_size = 25

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
        **kwargs,
    ) -> str:
        date_fmt = "%Y-%m-%d"
        params = {
            "ss": f"{city}, Sri Lanka",
            "checkin": checkin_date.strftime(date_fmt),
            "checkout": checkout_date.strftime(date_fmt),
            "group_adults": adults,
            "group_children": children,
            "no_rooms": rooms,
            "offset": offset,
        }
        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.base_url}/searchresults.html?{query}"

    def has_next_page(self, html: str) -> bool:
        soup = self.parser.parse_with_soup(html)
        next_btn = soup.select_one("button[aria-label='Next page']")
        if not next_btn:
            return False
        if next_btn.has_attr("disabled"):
            return False
        if "disabled" in (next_btn.get("class") or []):
            return False
        return True

    def _has_next_page(self, html: str) -> bool:
        """Backward-compatible alias used by tests."""
        return self.has_next_page(html)

    @staticmethod
    def get_popular_cities_sri_lanka() -> List[str]:
        return TravelSiteScraper.get_popular_cities_sri_lanka()
