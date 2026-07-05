"""Tests for the FastAPI layer (src/api)."""

import pytest
from fastapi.testclient import TestClient

from src.api.deps import get_storage
from src.api.main import app
from src.storage.database import DatabaseStorage


@pytest.fixture
def test_db_url(tmp_path):
    """File-backed sqlite DB so data persists across the multiple
    engine instances created per-request (unlike sqlite:///:memory:,
    which would start fresh on every connection)."""
    return f"sqlite:///{tmp_path / 'test_api.db'}"


@pytest.fixture
def client(test_db_url, monkeypatch):
    app.dependency_overrides[get_storage] = lambda: DatabaseStorage(test_db_url)
    monkeypatch.setattr(
        "src.api.routers.scrape.DatabaseStorage",
        lambda *a, **kw: DatabaseStorage(test_db_url),
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_top_hotels_empty(client):
    resp = client.get("/api/hotels/top")
    assert resp.status_code == 200
    assert resp.json() == []


def test_top_hotels_and_listing(client, test_db_url, sample_hotel_records):
    DatabaseStorage(test_db_url).save(sample_hotel_records)

    top = client.get("/api/hotels/top").json()
    assert len(top) == 3
    assert all(h["checkin_count"] == 1 for h in top)

    listing = client.get("/api/hotels", params={"limit": 2}).json()
    assert listing["total"] == 3
    assert len(listing["items"]) == 2

    filtered = client.get("/api/hotels", params={"source": "agoda"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["hotel_name"] == "Heritance Kandalama"


def test_monthly_stats(client, test_db_url, sample_hotel_records):
    DatabaseStorage(test_db_url).save(sample_hotel_records)

    resp = client.get("/api/stats/monthly", params={"year": 2026})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_checkins"] == 3
    assert data["monthly_totals"]["2026-07"] == 3


def test_meta_sources_and_cities(client):
    sources = client.get("/api/meta/sources").json()
    assert {"google", "sltda"}.issubset({s["id"] for s in sources})

    cities = client.get("/api/meta/cities").json()
    assert "Colombo" in cities


def test_last_scraped_endpoint(client, test_db_url, sample_hotel_records):
    storage = DatabaseStorage(test_db_url)
    storage.save(sample_hotel_records)
    storage.log_scrape_start("booking", "Colombo")
    storage.close()

    resp = client.get("/api/meta/last-scraped")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert len(data["sources"]) >= 5
    booking = next(row for row in data["sources"] if row["source"] == "booking")
    assert booking["records_in_db"] >= 1


def test_trigger_and_poll_scrape(client, monkeypatch):
    monkeypatch.setattr(
        "src.api.routers.scrape.run_source_scrape",
        lambda *a, **kw: [{"hotel_name": "Test Hotel"}],
    )

    resp = client.post(
        "/api/scrape",
        json={"source": "sltda", "city": "Colombo", "max_pages": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "started"

    status = client.get(f"/api/scrape/{body['log_id']}").json()
    assert status["status"] == "success"
    assert status["records_scraped"] == 1


def test_scrape_invalid_source(client):
    resp = client.post("/api/scrape", json={"source": "nope"})
    assert resp.status_code == 400


def test_scrape_status_not_found(client):
    resp = client.get("/api/scrape/999999")
    assert resp.status_code == 404
