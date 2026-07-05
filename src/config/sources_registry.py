"""Central registry of scrapeable sources."""

from typing import Dict, Set, Tuple

# Reliable travel sources (tested / HTTP or Playwright).
TRAVEL_SOURCES: Tuple[str, ...] = (
    "booking",
    "agoda",
    "expedia",
    "google",
)

# Government statistics (always HTTP, no anti-bot).
GOVERNMENT_SOURCES: Tuple[str, ...] = (
    "sltda",
)

ALL_SOURCES: Tuple[str, ...] = TRAVEL_SOURCES + GOVERNMENT_SOURCES

VALID_SOURCES: Set[str] = set(ALL_SOURCES)

PLAYWRIGHT_DEFAULT_SOURCES: Set[str] = {
    "agoda",
    "expedia",
    "google",
}

SOURCE_LABELS: Dict[str, str] = {
    "booking": "Booking.com",
    "agoda": "Agoda",
    "expedia": "Expedia",
    "google": "Google Hotels",
    "sltda": "SLTDA (Sri Lanka Tourism Development Authority)",
}

SOURCE_LEGAL_NOTES: Dict[str, str] = {
    "booking": "Commercial site. Requires Playwright when blocked. Respect robots.txt.",
    "agoda": "Commercial site, JS-heavy. Playwright recommended.",
    "expedia": "Commercial site. Playwright recommended.",
    "google": "Google Travel/Hotels search. Educational use; respect robots.txt and rate limits.",
    "sltda": "Government tourism statistics. Public & legal to scrape.",
}


def is_travel_source(source: str) -> bool:
    return source.lower() in TRAVEL_SOURCES


def is_government_source(source: str) -> bool:
    return source.lower() in GOVERNMENT_SOURCES
