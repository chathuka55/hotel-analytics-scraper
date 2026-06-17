"""Abstract base parser for all hotel data parsers."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from src.monitoring.logger import get_logger
from src.monitoring.metrics import get_metrics
from src.utils.validators import HotelCheckin, ValidationResult

logger = get_logger(__name__)


class BaseParser(ABC):
    """Abstract base class for all hotel data parsers.

    Provides common parsing utilities and defines the interface
    that all source-specific parsers must implement.
    """

    def __init__(self, source: str):
        """Initialize the parser.

        Args:
            source: Source identifier (booking, agoda, expedia, etc.)
        """
        self.source = source
        self.metrics = get_metrics()
        self.logger = get_logger(f"{self.__class__.__name__}")

    @abstractmethod
    def parse_search_results(
        self, html: str, city: str, checkin_date: date, checkout_date: date
    ) -> List[Dict[str, Any]]:
        """Parse hotel search results from HTML.

        Args:
            html: Raw HTML content
            city: City being searched
            checkin_date: Check-in date
            checkout_date: Check-out date

        Returns:
            List of parsed hotel data dictionaries
        """
        pass

    @abstractmethod
    def parse_hotel_detail(self, html: str, hotel_url: str) -> Dict[str, Any]:
        """Parse detailed hotel information from HTML.

        Args:
            html: Raw HTML content
            hotel_url: URL of the hotel page

        Returns:
            Dictionary with detailed hotel data
        """
        pass

    def parse_with_soup(self, html: str, parser: str = "lxml") -> BeautifulSoup:
        """Parse HTML into BeautifulSoup object.

        Args:
            html: Raw HTML string
            parser: Parser backend (lxml, html.parser, html5lib)

        Returns:
            BeautifulSoup object
        """
        with self.metrics.track_parse_time(self.source):
            return BeautifulSoup(html, parser)

    def extract_text(self, element, selector: str, default: str = "") -> str:
        """Safely extract text from a CSS selector.

        Args:
            element: BeautifulSoup element to search within
            selector: CSS selector string
            default: Default value if not found

        Returns:
            Extracted text or default
        """
        if element is None:
            return default
        found = element.select_one(selector)
        if found:
            return found.get_text(strip=True)
        return default

    def extract_attr(
        self, element, selector: str, attr: str, default: str = ""
    ) -> str:
        """Safely extract an attribute from a CSS selector.

        Args:
            element: BeautifulSoup element to search within
            selector: CSS selector string
            attr: Attribute name to extract
            default: Default value if not found

        Returns:
            Extracted attribute value or default
        """
        if element is None:
            return default
        found = element.select_one(selector)
        if found and found.has_attr(attr):
            return found[attr].strip()
        return default

    def extract_list(
        self, element, selector: str
    ) -> List[BeautifulSoup]:
        """Safely extract a list of elements matching a CSS selector.

        Args:
            element: BeautifulSoup element to search within
            selector: CSS selector string

        Returns:
            List of matching elements
        """
        if element is None:
            return []
        return element.select(selector)

    def validate_batch(
        self, records: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Validate a batch of parsed records.

        Args:
            records: List of parsed hotel data dictionaries

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        for i, record in enumerate(records):
            try:
                # Ensure source is set
                if "source" not in record or not record["source"]:
                    record["source"] = self.source

                hotel = HotelCheckin(**record)
                result.record_success()
                self.metrics.record_hotel_scraped(self.source, hotel.city)

            except Exception as e:
                error_msg = f"Record {i}: {str(e)}"
                result.add_error(error_msg)
                self.logger.warning(f"Validation failed: {error_msg}")

        self.logger.info(
            f"Validated {result.validated} records, "
            f"rejected {result.rejected}"
        )
        return result

    def clean_number(self, text: str) -> float:
        """Extract numeric value from text.

        Args:
            text: Text containing a number

        Returns:
            Extracted float value
        """
        if not text:
            return 0.0

        # Remove currency symbols, commas, and whitespace
        cleaned = "".join(c for c in text if c.isdigit() or c == ".")
        if cleaned:
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0

    def clean_integer(self, text: str) -> int:
        """Extract integer value from text.

        Args:
            text: Text containing an integer

        Returns:
            Extracted int value
        """
        return int(self.clean_number(text))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(source={self.source})"
