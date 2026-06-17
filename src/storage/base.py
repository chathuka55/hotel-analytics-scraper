"""Abstract base storage interface for all storage backends."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional


class BaseStorage(ABC):
    """Abstract base class for all storage implementations.

    Defines the interface that CSV, JSON, and database storage
    must implement to be used interchangeably in the pipeline.
    """

    @abstractmethod
    def save(self, records: List[Dict[str, Any]]) -> int:
        """Save a batch of records.

        Args:
            records: List of hotel data dictionaries

        Returns:
            Number of records saved
        """
        pass

    @abstractmethod
    def load(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        checkin_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load records with optional filtering.

        Args:
            source: Filter by source
            city: Filter by city
            checkin_date: Filter by check-in date
            limit: Maximum number of records

        Returns:
            List of matching records
        """
        pass

    @abstractmethod
    def get_top_hotels(
        self,
        city: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top hotels by check-in volume.

        Args:
            city: Filter by city
            month: Filter by month (1-12)
            year: Filter by year
            limit: Number of results

        Returns:
            List of top hotels with check-in counts
        """
        pass

    @abstractmethod
    def get_monthly_checkins(
        self,
        city: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly check-in statistics.

        Args:
            city: Filter by city
            year: Filter by year

        Returns:
            Dictionary with monthly aggregation data
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close storage connection and cleanup resources."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
