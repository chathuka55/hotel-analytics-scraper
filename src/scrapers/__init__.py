"""Scrapers package for hotel scraper."""

from .base import BaseScraper
from .booking import BookingScraper
from .agoda import AgodaScraper
from .expedia import ExpediaScraper
from .google import GoogleHotelsScraper
from .sltda import SLTDAScraper
from .travel import TravelSiteScraper

__all__ = [
    "BaseScraper",
    "TravelSiteScraper",
    "BookingScraper",
    "AgodaScraper",
    "ExpediaScraper",
    "GoogleHotelsScraper",
    "SLTDAScraper",
]
