"""Tests for storage backends."""

import json
import os
from datetime import date, datetime

import pytest

from src.storage.csv_storage import CSVStorage
from src.storage.database import DatabaseStorage
from src.storage.json_storage import JSONStorage


class TestCSVStorage:
    """Test cases for CSV storage."""

    def test_save_and_load(self, temp_dir, sample_hotel_records):
        """Test saving and loading records."""
        filepath = temp_dir / "test.csv"
        storage = CSVStorage(filepath=str(filepath))

        saved = storage.save(sample_hotel_records)
        assert saved == 3

        loaded = storage.load()
        assert len(loaded) == 3

    def test_filter_by_source(self, temp_dir, sample_hotel_records):
        """Test filtering by source."""
        filepath = temp_dir / "test.csv"
        storage = CSVStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        booking_results = storage.load(source="booking")
        assert len(booking_results) == 1
        assert booking_results[0]["source"] == "booking"

    def test_filter_by_city(self, temp_dir, sample_hotel_records):
        """Test filtering by city."""
        filepath = temp_dir / "test.csv"
        storage = CSVStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        colombo = storage.load(city="Colombo")
        assert len(colombo) == 1

    def test_top_hotels(self, temp_dir, sample_hotel_records):
        """Test top hotels aggregation."""
        filepath = temp_dir / "test.csv"
        storage = CSVStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        top = storage.get_top_hotels(limit=5)
        assert len(top) <= 3

    def test_monthly_checkins(self, temp_dir, sample_hotel_records):
        """Test monthly statistics."""
        filepath = temp_dir / "test.csv"
        storage = CSVStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        stats = storage.get_monthly_checkins(year=2026)
        assert stats["total_checkins"] == 3
        assert stats["total_unique_hotels"] == 3

    def test_context_manager(self, temp_dir):
        """Test context manager usage."""
        filepath = temp_dir / "test.csv"
        with CSVStorage(filepath=str(filepath)) as storage:
            assert storage is not None


class TestJSONStorage:
    """Test cases for JSON storage."""

    def test_save_and_load(self, temp_dir, sample_hotel_records):
        """Test saving and loading records."""
        filepath = temp_dir / "test.json"
        storage = JSONStorage(filepath=str(filepath))

        saved = storage.save(sample_hotel_records)
        assert saved == 3

        loaded = storage.load()
        assert len(loaded) == 3

    def test_append_mode(self, temp_dir, sample_hotel_records):
        """Test that saving appends to existing data."""
        filepath = temp_dir / "test.json"
        storage = JSONStorage(filepath=str(filepath))

        storage.save(sample_hotel_records[:2])
        storage.save(sample_hotel_records[2:])

        loaded = storage.load()
        assert len(loaded) == 3

    def test_date_serialization(self, temp_dir, sample_hotel_records):
        """Test that dates are properly serialized."""
        filepath = temp_dir / "test.json"
        storage = JSONStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        # Read raw JSON
        with open(filepath) as f:
            raw = json.load(f)

        assert isinstance(raw[0]["checkin_date"], str)

    def test_top_hotels(self, temp_dir, sample_hotel_records):
        """Test top hotels in JSON storage."""
        filepath = temp_dir / "test.json"
        storage = JSONStorage(filepath=str(filepath))
        storage.save(sample_hotel_records)

        top = storage.get_top_hotels(limit=5)
        assert len(top) > 0

    def test_context_manager(self, temp_dir):
        """Test context manager."""
        filepath = temp_dir / "test.json"
        with JSONStorage(filepath=str(filepath)) as storage:
            assert storage is not None


class TestDatabaseStorage:
    """Test cases for database storage."""

    def test_save_and_load(self, sample_hotel_records):
        """Test saving and loading records."""
        storage = DatabaseStorage("sqlite:///:memory:")

        saved = storage.save(sample_hotel_records)
        assert saved == 3

        loaded = storage.load()
        assert len(loaded) == 3

    def test_filter_by_source(self, sample_hotel_records):
        """Test filtering by source."""
        storage = DatabaseStorage("sqlite:///:memory:")
        storage.save(sample_hotel_records)

        booking = storage.load(source="booking")
        assert len(booking) == 1

    def test_filter_by_city(self, sample_hotel_records):
        """Test filtering by city."""
        storage = DatabaseStorage("sqlite:///:memory:")
        storage.save(sample_hotel_records)

        colombo = storage.load(city="Colombo")
        assert len(colombo) == 1

    def test_top_hotels(self, sample_hotel_records):
        """Test top hotels aggregation."""
        storage = DatabaseStorage("sqlite:///:memory:")
        storage.save(sample_hotel_records)

        top = storage.get_top_hotels(limit=5)
        assert len(top) > 0

    def test_monthly_checkins(self, sample_hotel_records):
        """Test monthly statistics."""
        storage = DatabaseStorage("sqlite:///:memory:")
        storage.save(sample_hotel_records)

        stats = storage.get_monthly_checkins(year=2026)
        assert "monthly_totals" in stats
        assert stats["total_checkins"] == 3

    def test_scrape_logging(self):
        """Test scrape log functionality."""
        storage = DatabaseStorage("sqlite:///:memory:")

        log_id = storage.log_scrape_start("booking", "Colombo")
        assert log_id > 0

        storage.log_scrape_complete(log_id, "success", 50, duration=120.5)

        history = storage.get_scrape_history()
        assert len(history) == 1
        assert history[0]["status"] == "success"
        assert history[0]["records_scraped"] == 50

    def test_multiple_saves(self, sample_hotel_records):
        """Test multiple save operations."""
        storage = DatabaseStorage("sqlite:///:memory:")

        storage.save(sample_hotel_records[:2])
        storage.save(sample_hotel_records[2:])

        loaded = storage.load()
        assert len(loaded) == 3

    def test_context_manager(self):
        """Test context manager."""
        with DatabaseStorage("sqlite:///:memory:") as storage:
            assert storage is not None

    def test_close(self):
        """Test connection cleanup."""
        storage = DatabaseStorage("sqlite:///:memory:")
        storage.close()
        # Should not raise


class TestStorageComparison:
    """Compare behavior across storage backends."""

    def test_consistent_results(self, temp_dir, sample_hotel_records):
        """All storages should return same results."""
        csv_storage = CSVStorage(filepath=str(temp_dir / "compare.csv"))
        json_storage = JSONStorage(filepath=str(temp_dir / "compare.json"))
        db_storage = DatabaseStorage("sqlite:///:memory:")

        csv_storage.save(sample_hotel_records)
        json_storage.save(sample_hotel_records)
        db_storage.save(sample_hotel_records)

        # All should have same count
        assert len(csv_storage.load()) == len(json_storage.load())
        assert len(json_storage.load()) == len(db_storage.load())

        # Same top hotels count
        csv_top = csv_storage.get_top_hotels(limit=5)
        json_top = json_storage.get_top_hotels(limit=5)
        db_top = db_storage.get_top_hotels(limit=5)

        assert len(csv_top) == len(json_top)
        assert len(json_top) == len(db_top)
