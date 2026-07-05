"""Static metadata endpoints (sources, cities) used to populate UI filters/forms."""

from fastapi import APIRouter, Depends

from src.api.deps import get_storage
from src.api.schemas import LastScrapedSummary, SourceInfo, SourceScrapeStatus
from src.config.sources_registry import (
    ALL_SOURCES,
    PLAYWRIGHT_DEFAULT_SOURCES,
    SOURCE_LABELS,
    SOURCE_LEGAL_NOTES,
)
from src.scrapers.booking import BookingScraper
from src.storage.database import DatabaseStorage

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


@router.get("/last-scraped", response_model=LastScrapedSummary)
def get_last_scraped(storage: DatabaseStorage = Depends(get_storage)):
    """When each source was last scraped and whether cached data is shown."""
    summary = storage.get_last_scraped_summary()
    return LastScrapedSummary(
        overall_last_scraped_at=summary.get("overall_last_scraped_at"),
        last_automation_run_at=summary.get("last_automation_run_at"),
        data_from_cache=summary.get("data_from_cache", False),
        sources=[SourceScrapeStatus(**row) for row in summary.get("sources", [])],
    )
