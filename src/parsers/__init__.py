"""Parsers package for hotel scraper."""

from .base import BaseParser
from .hotel_parser import HotelParser
from .review_parser import ReviewParser

__all__ = ["BaseParser", "HotelParser", "ReviewParser"]
