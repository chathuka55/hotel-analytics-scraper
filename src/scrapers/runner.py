"""Shared source-dispatch logic for running a single scraper.

Used by both the CLI (src/main.py) and the API's background scrape jobs
(src/api/routers/scrape.py) so the dispatch logic isn't duplicated.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from src.scrapers import (
    AgodaScraper,
    BookingScraper,
    DataGovLkScraper,
    ExpediaScraper,
    SLTDAScraper,
)


def run_source_scrape(
    source: str,
    storage,
    proxy,
    city: str,
    checkin: Optional[date],
    checkout: Optional[date],
    max_pages: int,
    use_playwright: Optional[bool],
    year: Optional[int],
    month: Optional[int],
) -> List[Dict[str, Any]]:
    """Scrape a single source.

    Args:
        source: Source identifier (booking, agoda, expedia, sltda, datagovlk)
        storage: Storage backend for saving results
        proxy: Optional proxy rotator
        city: City to search
        checkin: Check-in date
        checkout: Check-out date
        max_pages: Maximum pages to scrape
        use_playwright: Override browser automation usage
        year: Year for monthly analysis
        month: Month for monthly analysis

    Returns:
        List of scraped hotel records
    """

    if source == "booking":
        scraper = BookingScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else False

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "agoda":
        scraper = AgodaScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else True

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "expedia":
        scraper = ExpediaScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else True

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "sltda":
        scraper = SLTDAScraper(storage=storage, proxy_rotator=proxy)
        return scraper.scrape(year=year, month=month)

    elif source == "datagovlk":
        scraper = DataGovLkScraper(storage=storage, proxy_rotator=proxy)
        return scraper.scrape()

    return []
