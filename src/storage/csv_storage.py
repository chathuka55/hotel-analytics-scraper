"""CSV file storage for hotel data."""

import csv
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.monitoring.logger import get_logger
from src.storage.base import BaseStorage
from src.utils.validators import HotelCheckin

logger = get_logger(__name__)

CSV_COLUMNS = [
    "hotel_name",
    "source",
    "city",
    "country",
    "checkin_date",
    "checkout_date",
    "nightly_rate",
    "currency",
    "available_rooms",
    "occupancy_pct",
    "room_type",
    "guest_score",
    "review_count",
    "scraped_at",
    "url",
]


class CSVStorage(BaseStorage):
    """Store hotel data in CSV files.

    Simple, human-readable format good for:
    - Beginner level storage
    - Quick data inspection
    - Exporting to spreadsheets
    """

    def __init__(
        self,
        filepath: Optional[str] = None,
        data_dir: str = "data/raw",
        filename: Optional[str] = None,
    ):
        """Initialize CSV storage.

        Args:
            filepath: Full path to CSV file (overrides other options)
            data_dir: Directory for data files
            filename: Specific filename to use
        """
        if filepath:
            self._filepath = Path(filepath)
        else:
            data_dir_path = Path(data_dir)
            data_dir_path.mkdir(parents=True, exist_ok=True)

            if filename:
                self._filepath = data_dir_path / filename
            else:
                # Auto-generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._filepath = data_dir_path / f"hotels_{timestamp}.csv"

        self._ensure_headers()
        logger.info(f"CSV storage initialized: {self._filepath}")

    def _ensure_headers(self) -> None:
        """Write CSV headers if file doesn't exist."""
        if not self._filepath.exists() or self._filepath.stat().st_size == 0:
            with open(self._filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()

    def save(self, records: List[Dict[str, Any]]) -> int:
        """Save records to CSV.

        Args:
            records: List of hotel data dictionaries

        Returns:
            Number of records saved
        """
        if not records:
            return 0

        saved = 0
        with open(self._filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)

            for record in records:
                try:
                    # Normalize record to CSV format
                    row = self._record_to_row(record)
                    writer.writerow(row)
                    saved += 1
                except Exception as e:
                    logger.warning(f"Failed to write record to CSV: {e}")

        logger.info(f"Saved {saved} records to {self._filepath}")
        return saved

    def load(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        checkin_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load records from CSV with filtering.

        Args:
            source: Filter by source
            city: Filter by city
            checkin_date: Filter by check-in date
            limit: Maximum records to return

        Returns:
            List of matching records
        """
        if not self._filepath.exists():
            return []

        results = []
        with open(self._filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Apply filters
                if source and row.get("source", "").lower() != source.lower():
                    continue
                if city and row.get("city", "").lower() != city.lower():
                    continue
                if checkin_date and row.get("checkin_date") != checkin_date.isoformat():
                    continue

                # Convert types
                record = self._row_to_record(row)
                results.append(record)

                if limit and len(results) >= limit:
                    break

        return results

    def get_top_hotels(
        self,
        city: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top hotels by check-in count.

        Note: CSV storage does aggregation in-memory.
        For large datasets, use DatabaseStorage instead.
        """
        from collections import Counter

        records = self.load(city=city)
        hotel_counts = Counter()
        hotel_data = {}

        for record in records:
            checkin = record.get("checkin_date")
            if isinstance(checkin, str):
                try:
                    checkin = datetime.fromisoformat(checkin).date()
                except ValueError:
                    continue

            # Filter by month/year
            if month and checkin.month != month:
                continue
            if year and checkin.year != year:
                continue

            hotel_name = record.get("hotel_name", "Unknown")
            hotel_counts[hotel_name] += 1
            hotel_data[hotel_name] = record

        # Get top N
        top = hotel_counts.most_common(limit)
        return [
            {
                "hotel_name": name,
                "checkin_count": count,
                **{k: v for k, v in hotel_data.get(name, {}).items() if k != "hotel_name"},
            }
            for name, count in top
        ]

    def get_monthly_checkins(
        self,
        city: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly check-in statistics."""
        from collections import defaultdict

        records = self.load(city=city)
        monthly = defaultdict(int)
        hotels_by_month = defaultdict(set)

        for record in records:
            checkin = record.get("checkin_date")
            if isinstance(checkin, str):
                try:
                    checkin = datetime.fromisoformat(checkin).date()
                except ValueError:
                    continue

            if year and checkin.year != year:
                continue

            key = f"{checkin.year}-{checkin.month:02d}"
            monthly[key] += 1
            hotels_by_month[key].add(record.get("hotel_name", "Unknown"))

        return {
            "monthly_totals": dict(monthly),
            "unique_hotels_per_month": {
                k: len(v) for k, v in hotels_by_month.items()
            },
            "total_checkins": sum(monthly.values()),
            "total_unique_hotels": len(
                set(r.get("hotel_name") for r in records)
            ),
        }

    def close(self) -> None:
        """No-op for CSV storage."""
        pass

    def _record_to_row(self, record: Dict[str, Any]) -> Dict[str, str]:
        """Convert a record dict to CSV row format.

        Args:
            record: Hotel data dictionary

        Returns:
            Flat dictionary with string values
        """
        row = {}
        for col in CSV_COLUMNS:
            value = record.get(col, "")

            # Convert dates and datetimes to ISO strings
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            # Convert numbers
            elif isinstance(value, (int, float)):
                value = str(value)
            # Default empty
            elif value is None:
                value = ""

            row[col] = str(value)

        return row

    def _row_to_record(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Convert CSV row to typed record.

        Args:
            row: CSV row dictionary

        Returns:
            Record with proper types
        """
        record = dict(row)

        # Parse dates
        for date_field in ["checkin_date", "checkout_date"]:
            if record.get(date_field):
                try:
                    record[date_field] = datetime.fromisoformat(
                        record[date_field]
                    ).date()
                except ValueError:
                    pass

        # Parse datetime
        if record.get("scraped_at"):
            try:
                record["scraped_at"] = datetime.fromisoformat(
                    record["scraped_at"]
                )
            except ValueError:
                pass

        # Parse numbers
        for num_field in ["nightly_rate", "occupancy_pct", "guest_score"]:
            if record.get(num_field):
                try:
                    record[num_field] = float(record[num_field])
                except ValueError:
                    pass

        for int_field in ["available_rooms", "review_count"]:
            if record.get(int_field):
                try:
                    record[int_field] = int(record[int_field])
                except ValueError:
                    pass

        return record

    def get_filepath(self) -> str:
        """Get the current CSV file path."""
        return str(self._filepath)

    def __repr__(self) -> str:
        return f"CSVStorage({self._filepath})"
