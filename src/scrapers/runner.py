"""Shared source-dispatch logic for running a single scraper."""

from datetime import date
from typing import Any, Dict, List, Optional

from src.config.sources_registry import PLAYWRIGHT_DEFAULT_SOURCES, TRAVEL_SOURCES
from src.scrapers import (
    AgodaScraper,
    BookingScraper,
    ExpediaScraper,
    GoogleHotelsScraper,
    SLTDAScraper,
)


def _run_travel_scrape(
    source: str,
    storage,
    proxy,
    city: str,
    checkin: date,
    checkout: date,
    max_pages: int,
    use_playwright: Optional[bool],
    year: Optional[int],
    month: Optional[int],
) -> List[Dict[str, Any]]:
    scraper_cls = {
        "booking": BookingScraper,
        "agoda": AgodaScraper,
        "expedia": ExpediaScraper,
        "google": GoogleHotelsScraper,
    }[source]
    scraper = scraper_cls(storage=storage, proxy_rotator=proxy)

    if use_playwright is None:
        use_playwright = source in PLAYWRIGHT_DEFAULT_SOURCES

    if year and month:
        return scraper.scrape_with_monthly_dates(
            city=city, year=year, month=month, max_pages=max_pages
        )
    return scraper.scrape(
        city=city,
        checkin_date=checkin,
        checkout_date=checkout,
        max_pages=max_pages,
        use_playwright=use_playwright,
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
    source = source.lower()

    if source in TRAVEL_SOURCES:
        if not checkin or not checkout:
            if not (year and month):
                raise ValueError(
                    f"{source} requires checkin/checkout dates or year+month"
                )
        if checkin and checkout:
            return _run_travel_scrape(
                source,
                storage,
                proxy,
                city,
                checkin,
                checkout,
                max_pages,
                use_playwright,
                year,
                month,
            )
        return _run_travel_scrape(
            source,
            storage,
            proxy,
            city,
            checkin or date.today(),
            checkout or date.today(),
            max_pages,
            use_playwright,
            year,
            month,
        )

    if source == "sltda":
        scraper = SLTDAScraper(storage=storage, proxy_rotator=proxy)
        return scraper.scrape(year=year, month=month)

    return []
