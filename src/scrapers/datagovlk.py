"""data.gov.lk scraper for open government data.

Uses CKAN API for structured data access.
This is the most reliable way to access government data.
"""

import json
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.scrapers.base import BaseScraper
from src.storage.base import BaseStorage
from src.utils.proxies import ProxyRotator
from src.utils.validators import sanitize_text

logger = get_logger(__name__)


class DataGovLkScraper(BaseScraper):
    """Scraper for data.gov.lk open data portal.

    Uses the CKAN API for reliable data access.
    Falls back to HTML scraping if API is unavailable.
    """

    # CKAN API endpoints
    API_PACKAGE_LIST = "/api/3/action/package_list"
    API_PACKAGE_SEARCH = "/api/3/action/package_search"
    API_PACKAGE_SHOW = "/api/3/action/package_show"
    API_RESOURCE_SHOW = "/api/3/action/resource_show"

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("datagovlk", storage, proxy_rotator)
        self.base_url = get_settings().sources.datagovlk_base_url
        self.api_url = self.base_url  # CKAN API is on same domain

    def build_search_url(self, query: str = "tourism hotel", **kwargs) -> str:
        """Build search URL for data.gov.lk.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            Search URL
        """
        return (
            f"{self.api_url}{self.API_PACKAGE_SEARCH}"
            f"?q={query}&rows=100"
        )

    def scrape(
        self,
        query: str = "tourism hotel accommodation",
        max_datasets: int = 50,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape data.gov.lk for tourism datasets.

        Uses CKAN API for structured data retrieval.

        Args:
            query: Search query for datasets
            max_datasets: Maximum datasets to retrieve
            **kwargs: Additional parameters

        Returns:
            List of dataset metadata and data
        """
        all_results = []

        self.logger.info(
            f"Starting data.gov.lk scrape with query: {query}"
        )

        # Search for datasets via API
        try:
            datasets = self._search_datasets(query, max_datasets)
            self.logger.info(f"Found {len(datasets)} datasets")

            for dataset in datasets:
                try:
                    # Get full dataset details
                    dataset_details = self._get_dataset_details(
                        dataset["id"]
                    )

                    # Extract resources (files)
                    resources = dataset_details.get("resources", [])

                    for resource in resources:
                        resource_data = self._process_resource(resource)
                        if resource_data:
                            all_results.append({
                                "source": "datagovlk",
                                "record_type": "dataset_resource",
                                "dataset_name": dataset_details.get("title", ""),
                                "dataset_id": dataset["id"],
                                "resource_name": resource.get("name", ""),
                                "resource_format": resource.get("format", ""),
                                "resource_url": resource.get("url", ""),
                                "description": dataset_details.get("notes", ""),
                                "tags": [t["name"] for t in dataset_details.get("tags", [])],
                                "scraped_at": datetime.utcnow(),
                                "country": "Sri Lanka",
                                **resource_data,
                            })

                    time.sleep(1)  # Rate limiting

                except Exception as e:
                    self.logger.warning(
                        f"Error processing dataset {dataset.get('id')}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"API search failed: {e}")
            # Fallback to HTML scraping
            self.logger.info("Falling back to HTML scraping")
            html_results = self._scrape_html_fallback(query)
            all_results.extend(html_results)

        if all_results:
            self.save_results(all_results)

        self.logger.info(
            f"data.gov.lk scrape complete: {len(all_results)} records"
        )
        return all_results

    def _search_datasets(
        self, query: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for datasets using CKAN API.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of dataset summaries
        """
        url = f"{self.api_url}{self.API_PACKAGE_SEARCH}"
        params = {"q": query, "rows": limit}

        response = self.session_manager.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            raise Exception(f"API error: {data.get('error', 'Unknown')}")

        results = data["result"]["results"]
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "title": r.get("title", ""),
            }
            for r in results
        ]

    def _get_dataset_details(self, dataset_id: str) -> Dict[str, Any]:
        """Get full dataset details.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset details
        """
        url = f"{self.api_url}{self.API_PACKAGE_SHOW}"
        params = {"id": dataset_id}

        response = self.session_manager.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            raise Exception(f"API error: {data.get('error', 'Unknown')}")

        return data["result"]

    def _process_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Process a dataset resource.

        Args:
            resource: Resource metadata

        Returns:
            Processed resource data
        """
        result = {
            "resource_id": resource.get("id", ""),
            "created": resource.get("created", ""),
            "last_modified": resource.get("last_modified", ""),
            "size": resource.get("size", 0),
        }

        # Try to fetch data for CSV/JSON resources
        resource_url = resource.get("url", "")
        resource_format = resource.get("format", "").upper()

        if resource_format in ["CSV", "JSON"] and resource_url:
            try:
                preview = self._fetch_resource_preview(
                    resource_url, resource_format
                )
                result["data_preview"] = preview
            except Exception as e:
                self.logger.debug(f"Could not fetch preview: {e}")
                result["data_preview"] = None

        return result

    def _fetch_resource_preview(
        self, url: str, fmt: str, max_rows: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch a preview of resource data.

        Args:
            url: Resource URL
            fmt: File format
            max_rows: Maximum rows to fetch

        Returns:
            Data preview
        """
        response = self.session_manager.get(url, timeout=30)
        response.raise_for_status()

        if fmt == "JSON":
            data = response.json()
            if isinstance(data, list):
                return data[:max_rows]
            elif isinstance(data, dict):
                # Try common patterns
                for key in ["data", "results", "records"]:
                    if key in data and isinstance(data[key], list):
                        return data[key][:max_rows]
                return [data]

        elif fmt == "CSV":
            import csv
            from io import StringIO

            content = response.text
            reader = csv.DictReader(StringIO(content))
            return list(reader)[:max_rows]

        return []

    def _scrape_html_fallback(
        self, query: str = "tourism"
    ) -> List[Dict[str, Any]]:
        """Fallback HTML scraping for dataset discovery.

        Args:
            query: Search query

        Returns:
            List of dataset records
        """
        results = []

        try:
            search_url = f"{self.base_url}/dataset?q={query}"
            html = self.fetch_page(search_url)

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Find dataset items
            datasets = soup.select("li.dataset-item")

            for item in datasets:
                try:
                    title_elem = item.select_one("h3.dataset-heading a")
                    desc_elem = item.select_one("div.dataset-content div")

                    title = sanitize_text(title_elem.get_text()) if title_elem else ""
                    desc = sanitize_text(desc_elem.get_text()) if desc_elem else ""
                    url = title_elem["href"] if title_elem else ""

                    results.append({
                        "source": "datagovlk",
                        "record_type": "dataset",
                        "dataset_name": title,
                        "description": desc,
                        "dataset_url": (
                            url if url.startswith("http")
                            else f"{self.base_url}{url}"
                        ),
                        "scraped_at": datetime.utcnow(),
                        "country": "Sri Lanka",
                    })

                except Exception as e:
                    self.logger.debug(f"Error parsing dataset item: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"HTML fallback failed: {e}")

        return results

    def get_tourism_datasets(self) -> List[Dict[str, Any]]:
        """Get all tourism-related datasets.

        Returns:
            List of tourism datasets
        """
        return self.scrape(query="tourism")

    def get_hotel_datasets(self) -> List[Dict[str, Any]]:
        """Get hotel/accommodation-related datasets.

        Returns:
            List of hotel datasets
        """
        return self.scrape(query="hotel accommodation")

    def get_dataset_by_id(self, dataset_id: str) -> Dict[str, Any]:
        """Get a specific dataset by ID.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset details
        """
        return self._get_dataset_details(dataset_id)

    def list_all_datasets(self, limit: int = 100) -> List[str]:
        """List all available dataset names.

        Args:
            limit: Maximum number of datasets

        Returns:
            List of dataset names
        """
        url = f"{self.api_url}{self.API_PACKAGE_LIST}"

        try:
            response = self.session_manager.get(url)
            response.raise_for_status()

            data = response.json()
            if data.get("success"):
                return data["result"][:limit]
            return []

        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            return []
