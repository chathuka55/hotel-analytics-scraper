"""Tests for scrape status cache helpers."""

from pathlib import Path

from src.storage.scrape_cache import (
    append_run_summary,
    load_cache,
    save_cache,
    update_source_cache,
)


def test_cache_round_trip(tmp_path):
    cache_file = tmp_path / "scrape_status.json"
    cache = load_cache(cache_file)
    assert cache["sources"] == {}

    update_source_cache(
        cache,
        "booking",
        status="success",
        records_scraped=12,
        city="Colombo",
        data_last_scraped_at="2026-07-05T12:00:00",
    )
    append_run_summary(
        cache,
        {"completed_at": "2026-07-05T12:05:00", "records_scraped": 12},
    )
    save_cache(cache, cache_file)

    loaded = load_cache(cache_file)
    assert loaded["sources"]["booking"]["last_status"] == "success"
    assert loaded["sources"]["booking"]["records_scraped"] == 12
    assert loaded["last_automation_run_at"] == "2026-07-05T12:05:00"


def test_failed_source_marks_cached_data(tmp_path):
    cache_file = tmp_path / "scrape_status.json"
    cache = load_cache(cache_file)
    update_source_cache(
        cache,
        "google",
        status="success",
        data_last_scraped_at="2026-07-05T10:00:00",
    )
    update_source_cache(
        cache,
        "google",
        status="failed",
        error="site down",
        data_last_scraped_at="2026-07-05T10:00:00",
    )
    save_cache(cache, cache_file)

    loaded = load_cache(cache_file)
    assert loaded["sources"]["google"]["using_cached_data"] is True
    assert loaded["sources"]["google"]["last_error"] == "site down"
