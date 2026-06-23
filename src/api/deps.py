"""Shared FastAPI dependencies."""

from src.storage.database import DatabaseStorage


def get_storage():
    """Provide a DatabaseStorage instance for request handlers.

    The API always uses the database backend since it's the only storage
    that supports SQL aggregation (top hotels, monthly stats) and the
    ScrapeLog table used for scrape job status tracking. Each request gets
    its own engine/connection, closed once the request finishes.
    """
    storage = DatabaseStorage()
    try:
        yield storage
    finally:
        storage.close()
