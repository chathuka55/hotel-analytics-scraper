"""Hotel data parser with source-specific extraction logic."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config.settings import Selectors, get_selectors
from src.monitoring.logger import get_logger
from src.parsers.base import BaseParser
from src.utils.validators import parse_price, sanitize_text

logger = get_logger(__name__)


class HotelParser(BaseParser):
    """Parser for hotel listing and detail pages.

    Handles parsing for all supported sources with source-specific
    extraction logic based on CSS selectors.
    """

    def __init__(self, source: str):
        super().__init__(source)
        self.selectors: Selectors = get_selectors()

    def parse_search_results(
        self, html: str, city: str, checkin_date: date, checkout_date: date
    ) -> List[Dict[str, Any]]:
        """Parse hotel search results from HTML.

        Args:
            html: Raw HTML content from search page
            city: City being searched
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            List of parsed hotel data dictionaries
        """
        soup = self.parse_with_soup(html)
        results = []

        # Get source-specific selectors
        item_selector = self.selectors.get(self.source, "search_result_item")
        if not item_selector:
            logger.error(f"No search result selector for source: {self.source}")
            return results

        items = self.extract_list(soup, item_selector)
        logger.info(f"Found {len(items)} hotel elements on {self.source}")

        for item in items:
            try:
                hotel_data = self._parse_hotel_item(
                    item, city, checkin_date, checkout_date
                )
                if hotel_data and hotel_data.get("hotel_name"):
                    results.append(hotel_data)
            except Exception as e:
                logger.warning(f"Failed to parse hotel item: {e}")
                continue

        return results

    def parse_hotel_detail(self, html: str, hotel_url: str) -> Dict[str, Any]:
        """Parse detailed hotel information.

        Args:
            html: Raw HTML from hotel detail page
            hotel_url: URL of the hotel page

        Returns:
            Dictionary with detailed hotel information
        """
        soup = self.parse_with_soup(html)
        detail = {"url": hotel_url, "source": self.source}

        try:
            # Parse based on source
            detail.update(self._parse_detail_by_source(soup))
        except Exception as e:
            logger.error(f"Failed to parse hotel detail: {e}")

        return detail

    def _parse_hotel_item(
        self, item, city: str, checkin_date: date, checkout_date: date
    ) -> Dict[str, Any]:
        """Parse a single hotel item element.

        Args:
            item: BeautifulSoup element for one hotel
            city: City name
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            Dictionary with hotel data
        """
        data = {
            "source": self.source,
            "city": city,
            "country": "Sri Lanka",
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
        }

        # Hotel name
        name_selector = self.selectors.get(self.source, "hotel_name")
        if name_selector:
            data["hotel_name"] = sanitize_text(
                self.extract_text(item, name_selector)
            )

        # URL
        url_selector = self.selectors.get(self.source, "hotel_url")
        if url_selector:
            url = self.extract_attr(item, url_selector, "href")
            if url and not url.startswith("http"):
                # Relative URL - need to prepend base
                from src.config.settings import get_settings
                base = get_settings().get_source_url(self.source)
                url = base + url if base else url
            data["url"] = url

        # Price
        price_selector = self.selectors.get(self.source, "hotel_price")
        if price_selector:
            price_text = self.extract_text(item, price_selector)
            if price_text:
                amount, currency = parse_price(price_text)
                data["nightly_rate"] = amount
                data["currency"] = currency

        # Rating/Score
        score_selector = self.selectors.get(self.source, "hotel_score")
        if score_selector:
            score_text = self.extract_text(item, score_selector)
            if score_text:
                data["guest_score"] = self._parse_score(score_text)

        # Review count
        review_selector = self.selectors.get(self.source, "hotel_review_count")
        if review_selector:
            review_text = self.extract_text(item, review_selector)
            if review_text:
                data["review_count"] = self._extract_number(review_text)

        # Location
        location_selector = self.selectors.get(self.source, "hotel_location")
        if location_selector:
            data["room_type"] = sanitize_text(
                self.extract_text(item, location_selector)
            )

        return data

    def _parse_detail_by_source(self, soup) -> Dict[str, Any]:
        """Parse hotel detail page based on source-specific selectors.

        Args:
            soup: BeautifulSoup object of detail page

        Returns:
            Dictionary with detailed information
        """
        detail = {}

        # Hotel name
        name_sel = self.selectors.get(self.source, "detail_hotel_name")
        if name_sel:
            detail["hotel_name"] = sanitize_text(
                self.extract_text(soup, name_sel)
            )

        # Address
        addr_sel = self.selectors.get(self.source, "detail_address")
        if addr_sel:
            detail["address"] = sanitize_text(
                self.extract_text(soup, addr_sel)
            )

        # Rating
        rating_sel = self.selectors.get(self.source, "detail_rating")
        if rating_sel:
            rating_text = self.extract_text(soup, rating_sel)
            if rating_text:
                detail["guest_score"] = self._parse_score(rating_text)

        # Description
        desc_sel = self.selectors.get(self.source, "detail_description")
        if desc_sel:
            detail["description"] = sanitize_text(
                self.extract_text(soup, desc_sel)
            )

        # Facilities
        facil_sel = self.selectors.get(self.source, "detail_facilities")
        if facil_sel:
            facilities = self.extract_list(soup, facil_sel)
            detail["facilities"] = [
                sanitize_text(f.get_text()) for f in facilities
            ]

        # Coordinates
        coord_sel = self.selectors.get(self.source, "detail_coordinates")
        if coord_sel:
            coord_url = self.extract_attr(soup, coord_sel, "href", "")
            lat, lng = self._extract_coordinates(coord_url)
            if lat and lng:
                detail["latitude"] = lat
                detail["longitude"] = lng

        return detail

    def _parse_score(self, text: str) -> float:
        """Parse a score/rating from text.

        Handles formats like:
        - "8.5" -> 8.5
        - "8.5/10" -> 8.5
        - "85%" -> 8.5
        - "Excellent 8.5" -> 8.5

        Args:
            text: Score text

        Returns:
            Normalized score 0-10
        """
        if not text:
            return 0.0

        text = text.strip().lower()

        # Try to find a decimal or integer number
        match = re.search(r"(\d+[.,]?\d*)", text)
        if not match:
            return 0.0

        try:
            score = float(match.group(1).replace(",", "."))
        except ValueError:
            return 0.0

        # Normalize to 0-10 scale
        if "/5" in text:
            return min(10.0, max(0.0, score * 2))
        elif "%" in text:
            return min(10.0, max(0.0, score / 10))
        elif "/10" in text or score <= 10:
            return min(10.0, max(0.0, score))
        elif score > 10:  # Assume it's out of 100
            return min(10.0, score / 10)

        return min(10.0, max(0.0, score))

    def _extract_number(self, text: str) -> int:
        """Extract integer from text.

        Args:
            text: Text containing a number

        Returns:
            Extracted integer
        """
        if not text:
            return 0
        cleaned = re.sub(r"\D", "", text)
        try:
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0

    def _extract_coordinates(self, url: str) -> tuple:
        """Extract lat/lng from a maps URL.

        Args:
            url: Google Maps or similar URL

        Returns:
            Tuple of (latitude, longitude) or (None, None)
        """
        if not url:
            return None, None

        # Match patterns like @lat,lng or ?q=lat,lng
        patterns = [
            r"@(-?\d+\.\d+),(-?\d+\.\d+)",
            r"q=(-?\d+\.\d+),(-?\d+\.\d+)",
            r"ll=(-?\d+\.\d+),(-?\d+\.\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    return float(match.group(1)), float(match.group(2))
                except ValueError:
                    pass

        return None, None
