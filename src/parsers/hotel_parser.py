"""Hotel data parser with source-specific extraction logic."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config.settings import Selectors, get_selectors
from src.monitoring.logger import get_logger
from src.parsers.base import BaseParser
from src.utils.location import resolve_record_city
from src.utils.validators import is_junk_record, parse_price, sanitize_text

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
                if (
                    hotel_data
                    and hotel_data.get("hotel_name")
                    and not is_junk_record(hotel_data)
                ):
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
            "search_city": city,
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

        # Location / address (stored separately from room type)
        location_selector = self.selectors.get(self.source, "hotel_location")
        scraped_location = ""
        if location_selector:
            scraped_location = sanitize_text(
                self.extract_text(item, location_selector)
            )
            if scraped_location:
                data["address"] = scraped_location

        # Optional explicit city from listing (some sites show city separately)
        city_selector = self.selectors.get(self.source, "hotel_city")
        explicit_city = ""
        if city_selector:
            explicit_city = sanitize_text(
                self.extract_text(item, city_selector)
            )

        resolved_city, location_verified = resolve_record_city(
            scraped_location,
            city,
            explicit_city,
            hotel_name=data.get("hotel_name", ""),
            url=data.get("url", ""),
        )
        if location_verified and resolved_city:
            data["city"] = resolved_city
            data["location_verified"] = True
        else:
            # Do not inherit search city — prevents Galle-search/Kandy-hotel mislabels
            data["city"] = ""
            data["location_verified"] = False

        # Defaults for validation
        data.setdefault("nightly_rate", 0.0)
        data.setdefault("currency", "USD")
        data.setdefault("scraped_at", datetime.utcnow())

        # Room type (only when a dedicated selector exists)
        room_selector = self.selectors.get(self.source, "hotel_room_type")
        if room_selector:
            room_type = sanitize_text(self.extract_text(item, room_selector))
            if room_type:
                data["room_type"] = room_type

        # Try JSON-LD structured data for address/coordinates when CSS misses
        if not scraped_location:
            ld_data = self._extract_json_ld_location(item)
            if ld_data.get("address"):
                data["address"] = ld_data["address"]
                resolved_city, location_verified = resolve_record_city(
                    ld_data["address"],
                    city,
                    ld_data.get("city", ""),
                    hotel_name=data.get("hotel_name", ""),
                    url=data.get("url", ""),
                )
                if location_verified and resolved_city:
                    data["city"] = resolved_city
                    data["location_verified"] = True
            if ld_data.get("latitude") and ld_data.get("longitude"):
                data["latitude"] = ld_data["latitude"]
                data["longitude"] = ld_data["longitude"]

        # Last resort: scan card text for a city mention
        if not data.get("location_verified"):
            card_text = sanitize_text(item.get_text(" ", strip=True)[:800])
            resolved_city, location_verified = resolve_record_city(
                card_text, city, "", data.get("hotel_name", ""), data.get("url", "")
            )
            if location_verified and resolved_city:
                data["city"] = resolved_city
                data["location_verified"] = True
                if not data.get("address"):
                    data["address"] = card_text[:200]

        return data

    def _extract_json_ld_location(self, item) -> Dict[str, Any]:
        """Extract location from embedded JSON-LD in a listing element."""
        result: Dict[str, Any] = {}
        if item is None:
            return result

        scripts = item.select('script[type="application/ld+json"]')
        for script in scripts:
            try:
                import json

                payload = json.loads(script.string or "")
                items = payload if isinstance(payload, list) else [payload]
                for entry in items:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("@type") not in (
                        "Hotel",
                        "LodgingBusiness",
                        "Place",
                        None,
                    ):
                        continue
                    addr = entry.get("address", {})
                    if isinstance(addr, dict):
                        parts = [
                            addr.get("streetAddress", ""),
                            addr.get("addressLocality", ""),
                            addr.get("addressRegion", ""),
                        ]
                        address = ", ".join(p for p in parts if p)
                        if address:
                            result["address"] = sanitize_text(address)
                        if addr.get("addressLocality"):
                            result["city"] = sanitize_text(
                                addr["addressLocality"]
                            )
                    elif isinstance(addr, str) and addr:
                        result["address"] = sanitize_text(addr)
                    geo = entry.get("geo", {})
                    if isinstance(geo, dict):
                        if geo.get("latitude"):
                            result["latitude"] = float(geo["latitude"])
                        if geo.get("longitude"):
                            result["longitude"] = float(geo["longitude"])
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        return result

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
