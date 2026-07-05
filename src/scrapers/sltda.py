"""SLTDA (Sri Lanka Tourism Development Authority) scraper.

Government tourism statistics that are publicly available.
These sites are typically static HTML without JavaScript rendering.
"""

import re
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.scrapers.base import BaseScraper
from src.storage.base import BaseStorage
from src.utils.proxies import ProxyRotator
from src.utils.validators import sanitize_text

logger = get_logger(__name__)


class SLTDAScraper(BaseScraper):
    """Scraper for SLTDA government tourism data.

    SLTDA publishes monthly tourism statistics including:
    - Tourist arrivals by country
    - Hotel occupancy rates
    - Tourist accommodation data
    - Regional statistics

    This data is public and legally scrapable.
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
    ):
        super().__init__("sltda", storage, proxy_rotator)
        self.base_url = get_settings().sources.sltda_base_url
        self.parser.selectors = self._get_selectors()

    def _get_selectors(self):
        """Get SLTDA-specific selectors."""
        from src.config.settings import get_selectors
        return get_selectors()

    def build_search_url(self, **kwargs) -> str:
        """Build URL for SLTDA statistics page.

        Returns:
            URL to tourism statistics
        """
        # Main statistics page
        return f"{self.base_url}/en/statistics"

    def scrape(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Scrape SLTDA tourism statistics.

        Args:
            year: Year to filter
            month: Month to filter
            **kwargs: Additional parameters

        Returns:
            List of tourism statistics records
        """
        all_results = []

        self.logger.info("Starting SLTDA statistics scrape")

        # Scrape main statistics page
        try:
            url = self.build_search_url()
            html = self.fetch_page(url)
            stats = self._parse_statistics_page(html, year, month)
            all_results.extend(stats)
        except Exception as e:
            self.logger.error(f"Error scraping main stats: {e}")

        # Scrape monthly reports if available
        try:
            monthly_stats = self._scrape_monthly_reports(year, month)
            all_results.extend(monthly_stats)
        except Exception as e:
            self.logger.error(f"Error scraping monthly reports: {e}")

        # Scrape hotel occupancy data
        try:
            occupancy_data = self._scrape_hotel_occupancy(year, month)
            all_results.extend(occupancy_data)
        except Exception as e:
            self.logger.error(f"Error scraping occupancy data: {e}")

        if all_results:
            self.save_results(all_results)

        self.logger.info(f"SLTDA scrape complete: {len(all_results)} records")
        return all_results

    def _parse_statistics_page(
        self, html: str, year: Optional[int], month: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Parse the main statistics page.

        Args:
            html: HTML content
            year: Filter year
            month: Filter month

        Returns:
            List of statistics records
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Look for statistics tables
        tables = soup.find_all("table")
        self.logger.info(f"Found {len(tables)} tables on statistics page")

        for table in tables:
            try:
                records = self._parse_table(table, year, month)
                results.extend(records)
            except Exception as e:
                self.logger.debug(f"Failed to parse table: {e}")
                continue

        # Look for report links
        report_links = soup.select("a[href*='report']")
        for link in report_links:
            href = link.get("href", "")
            if href.endswith((".pdf", ".xlsx", ".xls")):
                self.logger.info(f"Found report: {link.get_text(strip=True)}")

        return results

    def _parse_table(
        self, table, year: Optional[int], month: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Parse a statistics table.

        Args:
            table: BeautifulSoup table element
            year: Filter year
            month: Filter month

        Returns:
            List of records from table
        """
        results = []
        rows = table.find_all("tr")

        if not rows:
            return results

        # Try to extract headers
        headers = []
        header_row = rows[0]
        for th in header_row.find_all(["th", "td"]):
            headers.append(sanitize_text(th.get_text()))

        # Parse data rows
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            cell_data = [sanitize_text(cell.get_text()) for cell in cells]

            if len(cell_data) < 2:
                continue

            # Try to identify what type of data this is
            record = self._identify_and_parse_record(headers, cell_data)

            if record:
                # Apply year/month filters
                if year and record.get("year") and record["year"] != year:
                    continue
                if month and record.get("month") and record["month"] != month:
                    continue

                results.append(record)

        return results

    def _identify_and_parse_record(
        self, headers: List[str], data: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Identify the type of record and parse it.

        Args:
            headers: Column headers
            data: Row data

        Returns:
            Parsed record or None
        """
        # Join for pattern matching
        header_text = " ".join(h.lower() for h in headers if h)
        data_text = " ".join(d for d in data if d)

        # Tourist arrivals pattern
        if any(k in header_text for k in ["arrival", "tourist", "visitor"]):
            return self._parse_arrival_record(headers, data)

        # Hotel occupancy pattern
        if any(k in header_text for k in ["occupancy", "room", "hotel"]):
            return self._parse_occupancy_record(headers, data)

        # Revenue/Expenditure pattern
        if any(k in header_text for k in ["revenue", "income", "earning"]):
            return self._parse_revenue_record(headers, data)

        # Generic record
        return self._parse_generic_record(headers, data)

    def _parse_arrival_record(
        self, headers: List[str], data: List[str]
    ) -> Dict[str, Any]:
        """Parse tourist arrival record.

        Args:
            headers: Column headers
            data: Row data

        Returns:
            Arrival record
        """
        record = {
            "source": "sltda",
            "record_type": "tourist_arrival",
            "country": "Sri Lanka",
            "scraped_at": datetime.utcnow(),
        }

        for i, (header, value) in enumerate(zip(headers, data)):
            header_lower = header.lower()

            if any(k in header_lower for k in ["country", "nationality", "market"]):
                record["origin_country"] = value
            elif any(k in header_lower for k in ["year", "period"]):
                year_match = re.search(r"\d{4}", value)
                if year_match:
                    record["year"] = int(year_match.group())
            elif any(k in header_lower for k in ["month"]):
                month_match = re.search(r"\d{1,2}", value)
                if month_match:
                    record["month"] = int(month_match.group())
            elif any(k in header_lower for k in ["arrival", "visitor", "tourist", "count", "number"]):
                num = re.sub(r"[^\d]", "", value)
                if num:
                    record["arrival_count"] = int(num)

        return record

    def _parse_occupancy_record(
        self, headers: List[str], data: List[str]
    ) -> Dict[str, Any]:
        """Parse hotel occupancy record.

        Args:
            headers: Column headers
            data: Row data

        Returns:
            Occupancy record
        """
        record = {
            "source": "sltda",
            "record_type": "hotel_occupancy",
            "country": "Sri Lanka",
            "scraped_at": datetime.utcnow(),
        }

        for i, (header, value) in enumerate(zip(headers, data)):
            header_lower = header.lower()

            if any(k in header_lower for k in ["hotel", "establishment", "property"]):
                record["hotel_name"] = value
            elif any(k in header_lower for k in ["region", "area", "district", "city"]):
                record["city"] = value
            elif any(k in header_lower for k in ["year"]):
                year_match = re.search(r"\d{4}", value)
                if year_match:
                    record["year"] = int(year_match.group())
            elif any(k in header_lower for k in ["month"]):
                month_match = re.search(r"\d{1,2}", value)
                if month_match:
                    record["month"] = int(month_match.group())
            elif any(k in header_lower for k in ["occupancy", "rate", "%"]):
                pct_match = re.search(r"\d+[.,]?\d*", value)
                if pct_match:
                    record["occupancy_pct"] = float(pct_match.group().replace(",", "."))
            elif any(k in header_lower for k in ["room", "night"]):
                num = re.sub(r"[^\d]", "", value)
                if num:
                    record["room_nights"] = int(num)

        return record

    def _parse_revenue_record(
        self, headers: List[str], data: List[str]
    ) -> Dict[str, Any]:
        """Parse revenue record.

        Args:
            headers: Column headers
            data: Row data

        Returns:
            Revenue record
        """
        record = {
            "source": "sltda",
            "record_type": "revenue",
            "country": "Sri Lanka",
            "scraped_at": datetime.utcnow(),
        }

        for header, value in zip(headers, data):
            header_lower = header.lower()

            if any(k in header_lower for k in ["year"]):
                year_match = re.search(r"\d{4}", value)
                if year_match:
                    record["year"] = int(year_match.group())
            elif any(k in header_lower for k in ["month"]):
                month_match = re.search(r"\d{1,2}", value)
                if month_match:
                    record["month"] = int(month_match.group())
            elif any(k in header_lower for k in ["revenue", "income", "earning"]):
                num = re.sub(r"[^\d.]", "", value)
                if num:
                    record["revenue_usd"] = float(num)

        return record

    def _parse_generic_record(
        self, headers: List[str], data: List[str]
    ) -> Dict[str, Any]:
        """Parse a generic record when type is unknown.

        Args:
            headers: Column headers
            data: Row data

        Returns:
            Generic record
        """
        record = {
            "source": "sltda",
            "record_type": "generic",
            "country": "Sri Lanka",
            "scraped_at": datetime.utcnow(),
        }

        for header, value in zip(headers, data):
            if header and value:
                key = header.lower().replace(" ", "_").replace("-", "_")[:50]
                record[key] = value

        return record

    def _scrape_monthly_reports(
        self, year: Optional[int], month: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Scrape monthly report links.

        Args:
            year: Filter year
            month: Filter month

        Returns:
            List of report metadata
        """
        results = []

        try:
            url = f"{self.base_url}/en/monthly-statistics"
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, "lxml")

            links = soup.select("a[href$='.pdf'], a[href$='.xlsx']")
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Extract year and month from link text
                year_match = re.search(r"\d{4}", text)
                month_match = re.search(
                    r"(January|February|March|April|May|June|July|August|"
                    r"September|October|November|December)",
                    text,
                    re.I,
                )

                report_year = int(year_match.group()) if year_match else None
                report_month = (
                    self._month_name_to_number(month_match.group())
                    if month_match
                    else None
                )

                # Apply filters
                if year and report_year and report_year != year:
                    continue
                if month and report_month and report_month != month:
                    continue

                results.append({
                    "source": "sltda",
                    "record_type": "monthly_report",
                    "report_title": text,
                    "report_url": href if href.startswith("http") else f"{self.base_url}{href}",
                    "year": report_year,
                    "month": report_month,
                    "country": "Sri Lanka",
                    "scraped_at": datetime.utcnow(),
                })

        except Exception as e:
            self.logger.error(f"Error fetching monthly reports: {e}")

        return results

    def _scrape_hotel_occupancy(
        self, year: Optional[int], month: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Scrape hotel occupancy statistics.

        Args:
            year: Filter year
            month: Filter month

        Returns:
            List of occupancy records
        """
        results = []

        try:
            # Try to find accommodation statistics page
            url = f"{self.base_url}/en/accommodation"
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, "lxml")

            # Look for occupancy tables
            tables = soup.find_all("table")
            for table in tables:
                records = self._parse_table(table, year, month)
                for record in records:
                    if record.get("record_type") == "hotel_occupancy":
                        results.append(record)

        except Exception as e:
            self.logger.error(f"Error fetching hotel occupancy: {e}")

        return results

    @staticmethod
    def _month_name_to_number(month_name: str) -> int:
        """Convert month name to number.

        Args:
            month_name: Month name

        Returns:
            Month number (1-12)
        """
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        return months.get(month_name.lower(), 0)

    def scrape_annual_report(self, year: int) -> List[Dict[str, Any]]:
        """Scrape annual tourism report.

        Args:
            year: Year to scrape

        Returns:
            Annual statistics
        """
        self.logger.info(f"Scraping annual report for {year}")

        return self.scrape(year=year)

    def get_tourism_arrivals_by_country(self, year: int) -> List[Dict[str, Any]]:
        """Get tourist arrivals broken down by country.

        Args:
            year: Year to analyze

        Returns:
            Arrivals by country
        """
        all_data = self.scrape(year=year)
        return [
            r for r in all_data
            if r.get("record_type") == "tourist_arrival"
            and r.get("origin_country")
        ]
