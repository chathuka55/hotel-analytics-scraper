"""Tests for automated scrape runner."""

import pytest

from src.automation.runner import run_automated_scrape
from src.storage.database import DatabaseStorage
from src.storage.scrape_cache import load_cache


@pytest.fixture
def test_db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'automation.db'}"


def test_automated_scrape_logs_and_cache(monkeypatch, test_db_url, tmp_path):
    from src.storage.scrape_cache import save_cache as write_cache

    cache_file = tmp_path / "cache" / "scrape_status.json"
    monkeypatch.setattr(
        "src.automation.runner.load_cache",
        lambda cf=None: load_cache(cache_file),
    )
    monkeypatch.setattr(
        "src.automation.runner.save_cache",
        lambda data, cf=None: write_cache(data, cache_file),
    )

    calls = {"count": 0}

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        if args[0] == "expedia":
            raise RuntimeError("blocked")
        return [{"hotel_name": "Test Hotel", "source": args[0], "city": "Colombo"}]

    monkeypatch.setattr("src.automation.runner.run_source_scrape", fake_run)

    storage = DatabaseStorage(test_db_url)
    summary = run_automated_scrape(
        storage=storage,
        sources=["booking", "expedia", "sltda"],
        cities=["Colombo"],
        own_storage=False,
    )

    assert summary["records_scraped"] >= 2
    assert calls["count"] == 3

    history = storage.get_scrape_history(limit=10)
    assert len(history) == 3
    assert any(row["status"] == "failed" and row["source"] == "expedia" for row in history)

    last = storage.get_last_scraped_summary()
    expedia = next(row for row in last["sources"] if row["source"] == "expedia")
    assert expedia["last_status"] == "failed"

    storage.close()
