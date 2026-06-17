"""Tests for Booking.com scraper."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import responses

from src.scrapers.booking import BookingScraper
from src.storage.csv_storage import CSVStorage


class TestBookingScraper:
    """Test cases for BookingScraper."""

    @pytest.fixture
    def scraper(self, temp_dir):
        """Create a BookingScraper instance."""
        storage = CSVStorage(filepath=str(temp_dir / "booking_test.csv"))
        return BookingScraper(storage=storage)

    def test_build_search_url(self, scraper):
        """Test URL construction."""
        url = scraper.build_search_url(
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        assert "Colombo" in url
        assert "2026-07-15" in url
        assert "2026-07-18" in url
        assert "booking.com" in url

    def test_build_search_url_with_params(self, scraper):
        """Test URL with additional parameters."""
        url = scraper.build_search_url(
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
            adults=4,
            children=2,
            rooms=2,
            offset=25,
        )

        assert "group_adults=4" in url
        assert "no_rooms=2" in url
        assert "offset=25" in url

    @responses.activate
    def test_fetch_page(self, scraper):
        """Test page fetching."""
        html = "<html><body>Test</body></html>"
        responses.add(
            responses.GET,
            "https://www.booking.com/test",
            body=html,
            status=200,
            content_type="text/html",
        )

        # Patch session manager to use responses
        scraper.session_manager.session.get = MagicMock(
            return_value=MagicMock(
                status_code=200, text=html, raise_for_status=lambda: None
            )
        )

        result = scraper.fetch_page("https://www.booking.com/test")
        assert "Test" in result

    def test_parse_results(self, scraper, mock_booking_html):
        """Test HTML result parsing."""
        results = scraper.parse_results(
            html=mock_booking_html,
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        assert len(results) == 2
        assert results[0]["hotel_name"] == "Cinnamon Grand Colombo"

    def test_has_next_page_true(self, scraper):
        """Test next page detection - has next."""
        html = '<button aria-label="Next page"></button>'
        assert scraper._has_next_page(html) is True

    def test_has_next_page_disabled(self, scraper):
        """Test next page detection - disabled."""
        html = '<button aria-label="Next page" disabled></button>'
        assert scraper._has_next_page(html) is False

    def test_has_next_page_missing(self, scraper):
        """Test next page detection - no button."""
        html = "<html></html>"
        assert scraper._has_next_page(html) is False

    def test_popular_cities(self, scraper):
        """Test popular cities list."""
        cities = scraper.get_popular_cities_sri_lanka()
        assert "Colombo" in cities
        assert "Kandy" in cities
        assert "Galle" in cities
        assert len(cities) > 10

    @responses.activate
    def test_scrape_with_mock(self, scraper, mock_booking_html):
        """Test full scrape flow with mocked HTTP."""
        search_url = scraper.build_search_url(
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        # Mock the fetch_page method
        with patch.object(scraper, "fetch_page", return_value=mock_booking_html):
            with patch.object(
                scraper, "_has_next_page", return_value=False
            ):
                results = scraper.scrape(
                    city="Colombo",
                    checkin_date=date(2026, 7, 15),
                    checkout_date=date(2026, 7, 18),
                    max_pages=1,
                    use_playwright=False,
                )

        assert len(results) == 2
        assert all(r["source"] == "booking" for r in results)

    def test_scraper_context_manager(self, temp_dir):
        """Test using scraper as context manager."""
        storage = CSVStorage(filepath=str(temp_dir / "test.csv"))

        with BookingScraper(storage=storage) as scraper:
            assert scraper.source == "booking"

    def test_stats_tracking(self, scraper, mock_booking_html):
        """Test statistics are tracked."""
        with patch.object(scraper, "fetch_page", return_value=mock_booking_html):
            with patch.object(scraper, "_has_next_page", return_value=False):
                scraper.scrape(
                    city="Colombo",
                    checkin_date=date(2026, 7, 15),
                    checkout_date=date(2026, 7, 18),
                    max_pages=1,
                    use_playwright=False,
                )

        stats = scraper.get_stats()
        assert stats["source"] == "booking"
        assert stats["hotels"] > 0
