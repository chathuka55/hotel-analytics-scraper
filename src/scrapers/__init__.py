"""Scrapers package for hotel scraper."""

from .base import BaseScraper
from .booking import BookingScraper
from .agoda import AgodaScraper
from .expedia import ExpediaScraper
from .sltda import SLTDAScraper
from .datagovlk import DataGovLkScraper

__all__ = [
    "BaseScraper",
    "BookingScraper",
    "AgodaScraper",
    "ExpediaScraper",
    "SLTDAScraper",
    "DataGovLkScraper",
]
