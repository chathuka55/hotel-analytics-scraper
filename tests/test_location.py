"""Tests for location normalization and city extraction."""

from src.utils.location import (
    extract_city_from_location,
    extract_city_from_url,
    normalize_city,
    parse_city_from_text,
    resolve_record_city,
)


class TestLocationUtils:
    def test_normalize_city_aliases(self):
        assert normalize_city("colombo city") == "Colombo"
        assert normalize_city("KANDY") == "Kandy"

    def test_extract_city_from_address(self):
        assert parse_city_from_text("123 Main St, Kandy, Sri Lanka") == "Kandy"
        assert parse_city_from_text("77 Galle Road, Colombo 03") == "Colombo"

    def test_galle_road_colombo_not_galle(self):
        assert parse_city_from_text("77 Galle Road, Colombo") == "Colombo"

    def test_search_city_fallback_only_when_empty(self):
        assert extract_city_from_location("", "Galle") == "Galle"
        assert extract_city_from_location("2 km from beach", "Galle") == ""

    def test_resolve_prefers_scraped_over_search(self):
        city, verified = resolve_record_city(
            "Peradeniya Road, Kandy, Sri Lanka",
            search_city="Galle",
        )
        assert city == "Kandy"
        assert verified is True

    def test_resolve_rejects_unverified_search_city(self):
        city, verified = resolve_record_city("", search_city="Galle")
        assert city == ""
        assert verified is False

    def test_resolve_from_hotel_name(self):
        city, verified = resolve_record_city(
            "",
            search_city="Galle",
            hotel_name="Earl's Regency Hotel Kandy",
        )
        assert city == "Kandy"
        assert verified is True

    def test_resolve_from_url(self):
        city, verified = resolve_record_city(
            "",
            search_city="Colombo",
            url="https://www.booking.com/hotel/lk/kandy-view.html",
        )
        assert city == "Kandy"
        assert verified is True

    def test_extract_city_from_url_helper(self):
        assert extract_city_from_url("/hotel/lk/heritance-kandalama-dambulla") == "Dambulla"
