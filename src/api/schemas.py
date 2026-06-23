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
    raw_data: Optional[Dict[str, Any]] = None


class HotelListResponse(BaseModel):
    """Paginated listing of raw hotel records."""

    items: List[HotelRecord]
    total: int


class ScrapeRequest(BaseModel):
    """Request body to trigger a scrape job."""

    source: str = Field(..., description="booking, agoda, expedia, sltda, datagovlk")
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
