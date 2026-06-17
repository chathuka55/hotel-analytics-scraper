"""JSON file storage for hotel data."""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.monitoring.logger import get_logger
from src.storage.base import BaseStorage

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles dates and datetimes."""

    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


class JSONStorage(BaseStorage):
    """Store hotel data in JSON files.

    Good for:
    - Nested data structures
    - API responses
    - Human-readable structured data
    """

    def __init__(
        self,
        filepath: Optional[str] = None,
        data_dir: str = "data/raw",
        filename: Optional[str] = None,
        indent: Optional[int] = 2,
    ):
        """Initialize JSON storage.

        Args:
            filepath: Full path to JSON file
            data_dir: Directory for data files
            filename: Specific filename
            indent: JSON indentation (None for compact)
        """
        if filepath:
            self._filepath = Path(filepath)
        else:
            data_dir_path = Path(data_dir)
            data_dir_path.mkdir(parents=True, exist_ok=True)

            if filename:
                self._filepath = data_dir_path / filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._filepath = data_dir_path / f"hotels_{timestamp}.json"

        self._indent = indent
        self._ensure_file()
        logger.info(f"JSON storage initialized: {self._filepath}")

    def _ensure_file(self) -> None:
        """Create empty JSON array if file doesn't exist."""
        if not self._filepath.exists():
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load_all(self) -> List[Dict[str, Any]]:
        """Load all records from JSON file."""
        if not self._filepath.exists():
            return []
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_all(self, records: List[Dict[str, Any]]) -> None:
        """Save all records to JSON file."""
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, cls=DateTimeEncoder, indent=self._indent, ensure_ascii=False)

    def save(self, records: List[Dict[str, Any]]) -> int:
        """Save records to JSON file.

        Args:
            records: List of hotel data dictionaries

        Returns:
            Number of records saved
        """
        if not records:
            return 0

        existing = self._load_all()

        # Normalize records for JSON serialization
        normalized = []
        for record in records:
            norm = {}
            for k, v in record.items():
                if isinstance(v, (date, datetime)):
                    norm[k] = v.isoformat()
                elif isinstance(v, (int, float, str, bool, list, dict)):
                    norm[k] = v
                elif v is not None:
                    norm[k] = str(v)
                else:
                    norm[k] = None
            normalized.append(norm)

        existing.extend(normalized)
        self._save_all(existing)

        logger.info(f"Saved {len(records)} records to {self._filepath}")
        return len(records)

    def load(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        checkin_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load records with filtering."""
        records = self._load_all()
        results = []

        for record in records:
            if source and record.get("source", "").lower() != source.lower():
                continue
            if city and record.get("city", "").lower() != city.lower():
                continue
            if checkin_date:
                rec_date = record.get("checkin_date", "")
                if isinstance(rec_date, str) and rec_date != checkin_date.isoformat():
                    continue

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
        """Get top hotels by check-in count."""
        from collections import Counter

        records = self.load(city=city)
        hotel_counts = Counter()
        hotel_data = {}

        for record in records:
            checkin = record.get("checkin_date", "")
            if isinstance(checkin, str):
                try:
                    checkin = datetime.fromisoformat(checkin).date()
                except ValueError:
                    continue

            if month and checkin.month != month:
                continue
            if year and checkin.year != year:
                continue

            name = record.get("hotel_name", "Unknown")
            hotel_counts[name] += 1
            hotel_data[name] = record

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
            checkin = record.get("checkin_date", "")
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
        """No-op for JSON storage."""
        pass

    def get_filepath(self) -> str:
        """Get the current JSON file path."""
        return str(self._filepath)

    def __repr__(self) -> str:
        return f"JSONStorage({self._filepath})"
