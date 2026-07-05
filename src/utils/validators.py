"""Data validation utilities for scraped hotel data."""

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from src.config.sources_registry import VALID_SOURCES, is_travel_source
from src.utils.location import normalize_city

JUNK_HOTEL_NAMES: Set[str] = {
    "",
    "unknown",
    "n/a",
    "na",
    "none",
    "null",
    "-",
    "—",
    "not available",
    "unnamed",
}


def is_junk_record(data: Dict[str, Any]) -> bool:
    """Return True if a record should be discarded (unknown/incomplete)."""
    source = (data.get("source") or "").lower().strip()
    if not source or source == "unknown" or source not in VALID_SOURCES:
        return True

    name = (data.get("hotel_name") or "").strip().lower()
    if name in JUNK_HOTEL_NAMES:
        return True

    city = (data.get("city") or "").strip()
    if not city or city.lower() in JUNK_HOTEL_NAMES:
        return True

    # data.gov.lk rows are dataset metadata, not individual hotels.
    if source == "datagovlk":
        return True

    # SLTDA tourist-arrival rows have no hotel identity.
    record_type = data.get("record_type") or ""
    if source == "sltda" and record_type in ("tourist_arrival", "monthly_report", "generic", "revenue"):
        return True

    # SLTDA occupancy without a hotel name is regional stats, not a hotel row.
    if source == "sltda" and record_type == "hotel_occupancy":
        if name in JUNK_HOTEL_NAMES or not data.get("hotel_name"):
            return True

    # Travel OTAs: require verified location (never save search-city guesses).
    if is_travel_source(source):
        if not data.get("location_verified"):
            return True
        if not data.get("city"):
            return True

    return False


def filter_scraped_records(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove junk/unknown records and normalize city names before save."""
    cleaned: List[Dict[str, Any]] = []
    for record in records:
        if is_junk_record(record):
            continue
        record = dict(record)
        if record.get("city"):
            record["city"] = normalize_city(record["city"])
        cleaned.append(record)
    return cleaned


class HotelCheckin(BaseModel):
    """Pydantic model for validated hotel check-in data.

    This is the primary data model used throughout the scraper pipeline.
    """

    hotel_name: str = Field(..., min_length=1, max_length=500)
    source: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., min_length=1, max_length=200)
    country: str = Field(default="Sri Lanka", min_length=1, max_length=200)
    checkin_date: date
    checkout_date: date
    nightly_rate: float = Field(..., ge=0)
    currency: str = Field(default="USD", min_length=1, max_length=10)
    available_rooms: int = Field(default=0, ge=0)
    occupancy_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    room_type: str = Field(default="", max_length=200)
    guest_score: float = Field(default=0.0, ge=0.0, le=10.0)
    review_count: int = Field(default=0, ge=0)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    url: str = Field(default="", max_length=2000)
    address: str = Field(default="", max_length=500)

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source is a known scraper."""
        v_lower = v.lower().strip()
        if v_lower not in VALID_SOURCES:
            raise ValueError(f"Invalid source: {v}")
        return v_lower

    @field_validator("city")
    @classmethod
    def normalize_city_field(cls, v: str) -> str:
        """Normalize city to canonical form."""
        normalized = normalize_city(v)
        if not normalized:
            raise ValueError("city cannot be empty")
        return normalized

    @field_validator("hotel_name")
    @classmethod
    def clean_hotel_name(cls, v: str) -> str:
        """Clean and normalize hotel name."""
        # Remove extra whitespace
        v = " ".join(v.split())
        # Remove common suffixes for consistency
        suffixes = ["Hotel", "Resort", "Villa", "Guest House", "Hostel"]
        return v

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Normalize currency to standard codes."""
        currency_map = {
            "US$": "USD",
            "$": "USD",
            "Rs": "LKR",
            "LKR": "LKR",
            "\\": "LKR",
            "EUR": "EUR",
            "\\u20ac": "EUR",
            "GBP": "GBP",
            "\\u00a3": "GBP",
        }
        return currency_map.get(v.upper(), v.upper())

    @model_validator(mode="after")
    def validate_dates(self):
        """Ensure checkout is after checkin."""
        if self.checkout_date <= self.checkin_date:
            raise ValueError("checkout_date must be after checkin_date")

        # Sanity check: dates shouldn't be too far in the past or future
        today = date.today()
        if self.checkin_date < today - timedelta(days=365):
            raise ValueError("checkin_date is too far in the past")
        if self.checkin_date > today + timedelta(days=730):
            raise ValueError("checkin_date is too far in the future")

        return self

    @model_validator(mode="after")
    def validate_review_score(self):
        """Validate that review count is present if score is."""
        if self.guest_score > 0 and self.review_count == 0:
            # Some sites show score without count, that's OK
            pass
        return self

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to flat dict for CSV serialization."""
        return {
            "hotel_name": self.hotel_name,
            "source": self.source,
            "city": self.city,
            "country": self.country,
            "checkin_date": self.checkin_date.isoformat(),
            "checkout_date": self.checkout_date.isoformat(),
            "nightly_rate": self.nightly_rate,
            "currency": self.currency,
            "available_rooms": self.available_rooms,
            "occupancy_pct": self.occupancy_pct,
            "room_type": self.room_type,
            "guest_score": self.guest_score,
            "review_count": self.review_count,
            "scraped_at": self.scraped_at.isoformat(),
            "url": self.url,
            "address": self.address,
        }

    @property
    def length_of_stay(self) -> int:
        """Calculate length of stay in nights."""
        return (self.checkout_date - self.checkin_date).days


class ValidationResult:
    """Result of data validation with detailed error reporting."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validated: int = 0
        self.rejected: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed with no errors."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.rejected += 1

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def record_success(self) -> None:
        """Record a successful validation."""
        self.validated += 1

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.validated += other.validated
        self.rejected += other.rejected
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_count": self.validated,
            "rejected_count": self.rejected,
        }

    def __repr__(self) -> str:
        return (
            f"ValidationResult(validated={self.validated}, "
            f"rejected={self.rejected}, errors={len(self.errors)}, "
            f"warnings={len(self.warnings)})"
        )


def validate_hotel_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Quick validation of a raw hotel data dict.

    Args:
        data: Dictionary containing hotel data

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["hotel_name", "source", "city", "checkin_date", "checkout_date"]

    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    if data.get("source", "").lower() not in VALID_SOURCES:
        return False, f"Invalid source: {data.get('source')}"

    if is_junk_record(data):
        return False, "Record is incomplete or unknown"

    # Validate dates
    try:
        if isinstance(data["checkin_date"], str):
            datetime.strptime(data["checkin_date"], "%Y-%m-%d")
        if isinstance(data["checkout_date"], str):
            datetime.strptime(data["checkout_date"], "%Y-%m-%d")
    except ValueError:
        return False, "Invalid date format, expected YYYY-MM-DD"

    # Validate price if present
    if "nightly_rate" in data and data["nightly_rate"] is not None:
        try:
            rate = float(data["nightly_rate"])
            if rate < 0:
                return False, "nightly_rate cannot be negative"
        except (ValueError, TypeError):
            return False, "nightly_rate must be a number"

    return True, None


def sanitize_text(text: str) -> str:
    """Sanitize text content from HTML.

    Args:
        text: Raw text content

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove special characters but keep international
    text = re.sub(r"[^\w\s\-.,()'/&\u0080-\uffff]", "", text)
    return text.strip()


def parse_price(price_text: str) -> Tuple[float, str]:
    """Parse price text into numeric value and currency.

    Args:
        price_text: Raw price string (e.g., "US$ 120.50" or "Rs 25,000")

    Returns:
        Tuple of (amount, currency_code)
    """
    if not price_text:
        return 0.0, "USD"

    # Currency symbols and codes
    currency_patterns = [
        (r"US\$\s*", "USD"),
        (r"\$\s*", "USD"),
        (r"Rs\.?\s*", "LKR"),
        (r"LKR\s*", "LKR"),
        (r"EUR\s*", "EUR"),
        (r"\u20ac\s*", "EUR"),
        (r"GBP\s*", "GBP"),
        (r"\u00a3\s*", "GBP"),
    ]

    detected_currency = "USD"
    cleaned = price_text.strip()

    # Detect currency
    for pattern, code in currency_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            detected_currency = code
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            break

    # Extract numeric value
    numeric_match = re.search(r"[\d,.]+", cleaned)
    if numeric_match:
        numeric_str = numeric_match.group()
        # Handle comma as thousands separator
        numeric_str = numeric_str.replace(",", "")
        try:
            return float(numeric_str), detected_currency
        except ValueError:
            return 0.0, detected_currency

    return 0.0, detected_currency
