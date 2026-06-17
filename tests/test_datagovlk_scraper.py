"""Tests for data.gov.lk scraper."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.scrapers.datagovlk import DataGovLkScraper
from src.storage.csv_storage import CSVStorage


class TestDataGovLkScraper:
    """Test cases for DataGovLkScraper."""

    @pytest.fixture
    def scraper(self, temp_dir):
        """Create scraper instance."""
        storage = CSVStorage(filepath=str(temp_dir / "datagovlk_test.csv"))
        return DataGovLkScraper(storage=storage)

    def test_build_search_url(self, scraper):
        """Test URL construction."""
        url = scraper.build_search_url(query="tourism")
        assert "data.gov.lk" in url
        assert "tourism" in url

    def test_search_datasets_mock(self, scraper):
        """Test dataset search with mock response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "results": [
                    {"id": "ds1", "name": "hotel-data", "title": "Hotel Statistics"},
                    {"id": "ds2", "name": "tourism-data", "title": "Tourism Data"},
                ]
            },
        }

        scraper.session_manager.get = MagicMock(return_value=mock_response)

        datasets = scraper._search_datasets("tourism")

        assert len(datasets) == 2
        assert datasets[0]["name"] == "hotel-data"

    def test_get_dataset_details_mock(self, scraper):
        """Test dataset detail retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "id": "ds1",
                "title": "Hotel Statistics",
                "notes": "Monthly hotel data",
                "resources": [
                    {
                        "id": "res1",
                        "name": "hotels.csv",
                        "format": "CSV",
                        "url": "https://example.com/hotels.csv",
                        "created": "2026-01-01",
                        "last_modified": "2026-06-01",
                        "size": 1024,
                    }
                ],
                "tags": [{"name": "tourism"}, {"name": "hotels"}],
            },
        }

        scraper.session_manager.get = MagicMock(return_value=mock_response)

        details = scraper._get_dataset_details("ds1")

        assert details["title"] == "Hotel Statistics"
        assert len(details["resources"]) == 1

    def test_process_resource_csv(self, scraper):
        """Test CSV resource processing."""
        resource = {
            "id": "res1",
            "name": "hotels.csv",
            "format": "CSV",
            "url": "https://example.com/hotels.csv",
            "created": "2026-01-01",
            "last_modified": "2026-06-01",
            "size": 1024,
        }

        mock_response = MagicMock()
        mock_response.text = "name,rooms\\nHotel A,100\\nHotel B,150"
        scraper.session_manager.get = MagicMock(return_value=mock_response)

        result = scraper._process_resource(resource)

        assert result["resource_id"] == "res1"
        assert "data_preview" in result

    def test_scrape_with_mock(self, scraper):
        """Test full scrape with mocked API."""
        search_response = MagicMock()
        search_response.json.return_value = {
            "success": True,
            "result": {
                "results": [{"id": "ds1", "name": "test", "title": "Test"}]
            },
        }

        detail_response = MagicMock()
        detail_response.json.return_value = {
            "success": True,
            "result": {
                "id": "ds1",
                "title": "Test Dataset",
                "notes": "Test data",
                "resources": [],
                "tags": [],
            },
        }

        def mock_get(url, **kwargs):
            if "package_search" in url:
                return search_response
            return detail_response

        scraper.session_manager.get = mock_get

        results = scraper.scrape(query="tourism")

        assert len(results) > 0
        assert results[0]["source"] == "datagovlk"

    def test_scrape_api_failure_fallback(self, scraper):
        """Test fallback to HTML on API failure."""
        error_response = MagicMock()
        error_response.json.return_value = {"success": False, "error": "API Error"}

        scraper.session_manager.get = MagicMock(return_value=error_response)

        # Mock HTML fallback
        with patch.object(
            scraper, "_scrape_html_fallback", return_value=[{"source": "datagovlk"}]
        ):
            results = scraper.scrape(query="tourism")

        assert len(results) > 0

    def test_fetch_resource_preview_json(self, scraper):
        """Test JSON resource preview."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "Hotel A"}, {"name": "Hotel B"}]

        scraper.session_manager.get = MagicMock(return_value=mock_response)

        preview = scraper._fetch_resource_preview("https://example.com/data.json", "JSON")

        assert len(preview) == 2

    def test_html_fallback(self, scraper):
        """Test HTML fallback scraping."""
        html = """
        <html>
            <li class="dataset-item">
                <h3 class="dataset-heading"><a href="/dataset/1">Tourism Data</a></h3>
                <div class="dataset-content"><div>Description here</div></div>
            </li>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html
        scraper.session_manager.get = MagicMock(return_value=mock_response)

        results = scraper._scrape_html_fallback("tourism")

        assert len(results) == 1
        assert results[0]["dataset_name"] == "Tourism Data"

    def test_list_all_datasets(self, scraper):
        """Test listing all datasets."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": ["dataset1", "dataset2", "dataset3"],
        }

        scraper.session_manager.get = MagicMock(return_value=mock_response)

        datasets = scraper.list_all_datasets()

        assert len(datasets) == 3

    def test_get_tourism_datasets(self, scraper):
        """Test tourism dataset retrieval."""
        with patch.object(scraper, "scrape", return_value=[{"id": "1"}]) as mock_scrape:
            results = scraper.get_tourism_datasets()

        mock_scrape.assert_called_once_with(query="tourism")
        assert len(results) == 1
