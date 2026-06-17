"""Storage package for hotel scraper."""

from .base import BaseStorage
from .csv_storage import CSVStorage
from .json_storage import JSONStorage
from .database import DatabaseStorage, init_db

__all__ = [
    "BaseStorage",
    "CSVStorage",
    "JSONStorage",
    "DatabaseStorage",
    "init_db",
]
