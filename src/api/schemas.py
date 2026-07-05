"""Pydantic response/request models for the API layer."""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TopHotel(BaseModel):
    """A single row in the top-hotels leaderboard."""

    hotel_name: str
    city: str
    checkin_count: int
    avg_nightly_rate: float
    avg_guest_score: float


class MonthlyStats(BaseModel):
    """Monthly check-in aggregation."""

    monthly_totals: Dict[str, int]
    unique_hotels_per_month: Dict[str, int]
    total_checkins: int
    total_unique_hotels: int
    total_cities: int


class RatedHotel(BaseModel):
    """A hotel row ranked by rating or value."""

    hotel_name: str
    city: str
    avg_guest_score: float
    avg_nightly_rate: float
    review_count: int = 0
    checkin_count: int = 0
    value_score: Optional[float] = None


class Overview(BaseModel):
    """Headline KPIs and the single best hotel per metric."""

    total_records: int
    total_hotels: int
    total_cities: int
    avg_nightly_rate: float
    min_nightly_rate: float
    max_nightly_rate: float
    avg_guest_score: float
    by_source: Dict[str, int]
    most_checkins: Optional[TopHotel] = None
    cheapest: Optional["HotelRecord"] = None
    best_rated: Optional[RatedHotel] = None
    best_value: Optional[RatedHotel] = None


class HotelRecord(BaseModel):
    """A single raw scraped hotel record."""

    id: int
    hotel_name: str
    source: str
    city: str
    country: str
    checkin_date: Optional[str] = None
    checkout_date: Optional[str] = None
    nightly_rate: float
    currency: str
    available_rooms: int
    occupancy_pct: float
    room_type: str
    guest_score: float
    review_count: int
    scraped_at: Optional[str] = None
    url: str
    address: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class HotelListResponse(BaseModel):
    """Paginated listing of raw hotel records."""

    items: List[HotelRecord]
    total: int


class ScrapeRequest(BaseModel):
    """Request body to trigger a scrape job."""

    source: str = Field(..., description="Any registered source id (see /api/meta/sources)")
    city: str = "Colombo"
    checkin_date: Optional[date] = None
    checkout_date: Optional[date] = None
    max_pages: int = Field(default=3, ge=1, le=20)


class ScrapeJobAccepted(BaseModel):
    """Response returned immediately after triggering a scrape job."""

    log_id: int
    status: str


class ScrapeJobStatus(BaseModel):
    """Status of a scrape job, polled by the UI."""

    id: int
    source: str
    city: str
    status: str
    records_scraped: int
    error_message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class SourceInfo(BaseModel):
    """Metadata about a scrapeable source."""

    id: str
    label: str
    requires_playwright: bool
    legal_note: str


class SourceScrapeStatus(BaseModel):
    """Last scrape timing and fallback state for one source."""

    source: str
    label: str
    last_scraped_at: Optional[str] = None
    last_attempt_at: Optional[str] = None
    last_status: str = "never"
    last_error: str = ""
    records_in_db: int = 0
    using_cached_data: bool = False


class LastScrapedSummary(BaseModel):
    """Aggregate scrape freshness shown in the dashboard."""

    overall_last_scraped_at: Optional[str] = None
    last_automation_run_at: Optional[str] = None
    data_from_cache: bool = False
    sources: List[SourceScrapeStatus]


# Resolve the forward reference to HotelRecord used in Overview.cheapest.
Overview.model_rebuild()
