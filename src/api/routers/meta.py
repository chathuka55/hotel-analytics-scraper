"""Static metadata endpoints (sources, cities) used to populate UI filters/forms."""

from fastapi import APIRouter

from src.api.schemas import SourceInfo
from src.config.sources_registry import (
    ALL_SOURCES,
    PLAYWRIGHT_DEFAULT_SOURCES,
    SOURCE_LABELS,
    SOURCE_LEGAL_NOTES,
)
from src.scrapers.booking import BookingScraper

router = APIRouter(prefix="/api/meta", tags=["meta"])

_SOURCES = [
    SourceInfo(
        id=source_id,
        label=SOURCE_LABELS.get(source_id, source_id.title()),
        requires_playwright=source_id in PLAYWRIGHT_DEFAULT_SOURCES,
        legal_note=SOURCE_LEGAL_NOTES.get(source_id, ""),
    )
    for source_id in ALL_SOURCES
]


@router.get("/sources", response_model=list[SourceInfo])
def get_sources():
    """List of scrapeable sources with playwright/legal metadata."""
    return _SOURCES


@router.get("/cities", response_model=list[str])
def get_cities():
    """Canonical list of popular Sri Lankan cities."""
    return BookingScraper.get_popular_cities_sri_lanka()
