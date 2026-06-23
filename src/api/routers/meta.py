"""Static metadata endpoints (sources, cities) used to populate UI filters/forms."""

from fastapi import APIRouter

from src.api.schemas import SourceInfo
from src.scrapers.booking import BookingScraper

router = APIRouter(prefix="/api/meta", tags=["meta"])

_SOURCES = [
    SourceInfo(
        id="booking",
        label="Booking.com",
        requires_playwright=False,
        legal_note="Commercial site. Respect robots.txt and rate limits.",
    ),
    SourceInfo(
        id="agoda",
        label="Agoda",
        requires_playwright=True,
        legal_note="Commercial site, JS-heavy. Respect robots.txt and rate limits.",
    ),
    SourceInfo(
        id="expedia",
        label="Expedia",
        requires_playwright=True,
        legal_note="Commercial site. Respect robots.txt and rate limits.",
    ),
    SourceInfo(
        id="sltda",
        label="SLTDA (Sri Lanka Tourism Development Authority)",
        requires_playwright=False,
        legal_note="Government tourism statistics. Public & legal to scrape.",
    ),
    SourceInfo(
        id="datagovlk",
        label="data.gov.lk",
        requires_playwright=False,
        legal_note="Open government data portal. Public & legal to scrape.",
    ),
]


@router.get("/sources", response_model=list[SourceInfo])
def get_sources():
    """List of scrapeable sources with playwright/legal metadata."""
    return _SOURCES


@router.get("/cities", response_model=list[str])
def get_cities():
    """Canonical list of popular Sri Lankan cities."""
    return BookingScraper.get_popular_cities_sri_lanka()
