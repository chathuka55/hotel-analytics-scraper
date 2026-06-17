"""Tests for SLTDA government scraper."""

from datetime import date
from unittest.mock import patch

import pytest

from src.scrapers.sltda import SLTDAScraper
from src.storage.csv_storage import CSVStorage


class TestSLTDAScraper:
    """Test cases for SLTDAScraper."""

    @pytest.fixture
    def scraper(self, temp_dir):
        """Create SLTDA scraper instance."""
        storage = CSVStorage(filepath=str(temp_dir / "sltda_test.csv"))
        return SLTDAScraper(storage=storage)

    def test_build_search_url(self, scraper):
        """Test URL construction."""
        url = scraper.build_search_url()
        assert "sltda.gov.lk" in url
        assert "statistics" in url

    def test_parse_statistics_page(self, scraper, mock_sltda_html):
        """Test statistics page parsing."""
        results = scraper._parse_statistics_page(mock_sltda_html, None, None)

        assert len(results) > 0

        # Check arrival records
        arrivals = [r for r in results if r.get("record_type") == "tourist_arrival"]
        assert len(arrivals) > 0
        assert any(r.get("origin_country") == "India" for r in arrivals)

    def test_parse_arrival_record(self, scraper):
        """Test arrival record parsing."""
        headers = ["Country", "Year", "Month", "Arrivals"]
        data = ["India", "2026", "January", "25,450"]

        record = scraper._parse_arrival_record(headers, data)

        assert record["origin_country"] == "India"
        assert record["arrival_count"] == 25450
        assert record["record_type"] == "tourist_arrival"

    def test_parse_occupancy_record(self, scraper):
        """Test occupancy record parsing."""
        headers = ["Region", "Year", "Occupancy Rate"]
        data = ["Colombo City", "2026", "78.5%"]

        record = scraper._parse_occupancy_record(headers, data)

        assert record["city"] == "Colombo City"
        assert record["occupancy_pct"] == 78.5
        assert record["record_type"] == "hotel_occupancy"

    def test_month_name_to_number(self, scraper):
        """Test month name conversion."""
        assert scraper._month_name_to_number("January") == 1
        assert scraper._month_name_to_number("December") == 12
        assert scraper._month_name_to_number("invalid") == 0

    def test_scrape_with_mock(self, scraper, mock_sltda_html):
        """Test full scrape with mocked HTTP."""
        with patch.object(scraper, "fetch_page", return_value=mock_sltda_html):
            results = scraper.scrape(year=2026)

        assert len(results) > 0

    def test_filter_by_year(self, scraper, mock_sltda_html):
        """Test year filtering."""
        results = scraper._parse_statistics_page(mock_sltda_html, year=2026, month=None)

        # All results should be from 2026
        for r in results:
            if "year" in r:
                assert r["year"] == 2026

    def test_filter_by_year_no_match(self, scraper, mock_sltda_html):
        """Test year filtering with no matches."""
        results = scraper._parse_statistics_page(mock_sltda_html, year=2020, month=None)

        # Should have no 2020 records
        year_records = [r for r in results if r.get("year") == 2020]
        assert len(year_records) == 0

    def test_parse_generic_record(self, scraper):
        """Test generic record parsing."""
        headers = ["Column A", "Column B"]
        data = ["Value 1", "Value 2"]

        record = scraper._parse_generic_record(headers, data)

        assert record["column_a"] == "Value 1"
        assert record["column_b"] == "Value 2"
        assert record["record_type"] == "generic"

    def test_parse_revenue_record(self, scraper):
        """Test revenue record parsing."""
        headers = ["Year", "Revenue"]
        data = ["2026", "$1,250,000"]

        record = scraper._parse_revenue_record(headers, data)

        assert record["record_type"] == "revenue"
        assert record["year"] == 2026

    def test_empty_html(self, scraper):
        """Test parsing empty HTML."""
        results = scraper._parse_statistics_page("<html></html>", None, None)
        assert len(results) == 0

    def test_tourism_arrivals_by_country(self, scraper, mock_sltda_html):
        """Test arrivals by country filtering."""
        with patch.object(scraper, "fetch_page", return_value=mock_sltda_html):
            arrivals = scraper.get_tourism_arrivals_by_country(2026)

        assert len(arrivals) > 0
        assert all(r.get("origin_country") for r in arrivals)
