"""Pytest configuration and shared fixtures."""

import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

# Ensure src is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# --- Path Fixtures ---

@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


# --- Mock Data Fixtures ---

@pytest.fixture
def sample_hotel_data():
    """Return a sample valid hotel record."""
    return {
        "hotel_name": "Cinnamon Grand Colombo",
        "source": "booking",
        "city": "Colombo",
        "country": "Sri Lanka",
        "checkin_date": date(2026, 7, 15),
        "checkout_date": date(2026, 7, 18),
        "nightly_rate": 150.00,
        "currency": "USD",
        "available_rooms": 25,
        "occupancy_pct": 85.5,
        "room_type": "Deluxe Room",
        "guest_score": 8.7,
        "review_count": 1250,
        "scraped_at": datetime.utcnow(),
        "url": "https://www.booking.com/hotel/lk/cinnamon-grand-colombo",
    }


@pytest.fixture
def sample_hotel_records():
    """Return multiple sample hotel records."""
    return [
        {
            "hotel_name": "Shangri-La Colombo",
            "source": "booking",
            "city": "Colombo",
            "country": "Sri Lanka",
            "checkin_date": date(2026, 7, 1),
            "checkout_date": date(2026, 7, 3),
            "nightly_rate": 200.00,
            "currency": "USD",
            "available_rooms": 15,
            "occupancy_pct": 92.0,
            "room_type": "Horizon Club",
            "guest_score": 9.1,
            "review_count": 890,
            "scraped_at": datetime.utcnow(),
            "url": "https://www.booking.com/hotel/lk/shangri-la",
        },
        {
            "hotel_name": "Heritance Kandalama",
            "source": "agoda",
            "city": "Dambulla",
            "country": "Sri Lanka",
            "checkin_date": date(2026, 7, 10),
            "checkout_date": date(2026, 7, 14),
            "nightly_rate": 180.00,
            "currency": "USD",
            "available_rooms": 30,
            "occupancy_pct": 78.5,
            "room_type": "Superior Room",
            "guest_score": 8.9,
            "review_count": 2100,
            "scraped_at": datetime.utcnow(),
            "url": "https://www.agoda.com/heritance-kandalama",
        },
        {
            "hotel_name": "The Fortress Resort",
            "source": "expedia",
            "city": "Galle",
            "country": "Sri Lanka",
            "checkin_date": date(2026, 7, 20),
            "checkout_date": date(2026, 7, 25),
            "nightly_rate": 350.00,
            "currency": "USD",
            "available_rooms": 8,
            "occupancy_pct": 65.0,
            "room_type": "Beach Villa",
            "guest_score": 9.3,
            "review_count": 450,
            "scraped_at": datetime.utcnow(),
            "url": "https://www.expedia.com/hotel/lk/fortress",
        },
    ]


@pytest.fixture
def invalid_hotel_data():
    """Return an invalid hotel record (missing required fields)."""
    return {
        "source": "booking",
        "city": "Colombo",
        # Missing hotel_name
        "checkin_date": date(2026, 7, 15),
        "checkout_date": date(2026, 7, 18),
    }


# --- HTML Mock Fixtures ---

@pytest.fixture
def mock_booking_html():
    """Return mock Booking.com search results HTML."""
    return """
    <html>
    <body>
        <div data-testid="property-card">
            <div data-testid="title">Cinnamon Grand Colombo</div>
            <a data-testid="title-link" href="/hotel/lk/cinnamon-grand.html">Link</a>
            <span data-testid="price-and-discounted-price">US$ 150</span>
            <div data-testid="review-score">
                <div>8.7</div>
                <abbr>1,250 reviews</abbr>
            </div>
            <span data-testid="address">77 Galle Road, Colombo</span>
            <img data-testid="image" src="/img1.jpg" alt="Hotel"/>
        </div>
        <div data-testid="property-card">
            <div data-testid="title">Shangri-La Colombo</div>
            <a data-testid="title-link" href="/hotel/lk/shangri-la.html">Link</a>
            <span data-testid="price-and-discounted-price">US$ 200</span>
            <div data-testid="review-score">
                <div>9.1</div>
                <abbr>890 reviews</abbr>
            </div>
            <span data-testid="address">1 Galle Face, Colombo</span>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_agoda_html():
    """Return mock Agoda search results HTML."""
    return """
    <html>
    <body>
        <li class="PropertyCard">
            <h3 class="sc-jrAGrp">Heritance Kandalama</h3>
            <a class="PropertyCard__Link" href="/heritance-kandalama/hotel/dambulla-lk.html">Link</a>
            <div class="sc-gkCoMD">
                <span>8.9</span>
                <span>2,100 reviews</span>
            </div>
            <span class="sc-dWOrae">US$ 180</span>
            <span class="sc-iBPRYJ">Dambulla</span>
            <img class="sc-kEqXSa" src="/img2.jpg" alt="Hotel"/>
        </li>
    </body>
    </html>
    """


@pytest.fixture
def mock_sltda_html():
    """Return mock SLTDA statistics page HTML."""
    return """
    <html>
    <body>
        <div class="statistics-section">
            <h2>Tourist Arrivals 2026</h2>
            <table>
                <tr>
                    <th>Country</th>
                    <th>Year</th>
                    <th>Month</th>
                    <th>Arrivals</th>
                </tr>
                <tr>
                    <td>India</td>
                    <td>2026</td>
                    <td>January</td>
                    <td>25,450</td>
                </tr>
                <tr>
                    <td>United Kingdom</td>
                    <td>2026</td>
                    <td>January</td>
                    <td>18,320</td>
                </tr>
                <tr>
                    <td>China</td>
                    <td>2026</td>
                    <td>January</td>
                    <td>15,780</td>
                </tr>
            </table>
        </div>
        <div class="statistics-section">
            <h2>Hotel Occupancy</h2>
            <table>
                <tr>
                    <th>Region</th>
                    <th>Year</th>
                    <th>Occupancy Rate</th>
                </tr>
                <tr>
                    <td>Colombo City</td>
                    <td>2026</td>
                    <td>78.5%</td>
                </tr>
                <tr>
                    <td>Kandy</td>
                    <td>2026</td>
                    <td>72.3%</td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """


# --- Mock Response Fixtures ---

@pytest.fixture
def mock_response_factory():
    """Factory for creating mock HTTP responses."""

    class MockResponse:
        def __init__(self, text="", status_code=200, headers=None):
            self.text = text
            self.status_code = status_code
            self.headers = headers or {}

        def json(self):
            import json
            return json.loads(self.text)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    return MockResponse


# --- Settings Fixture ---

@pytest.fixture
def test_settings():
    """Override settings for testing."""
    from src.config.settings import Settings

    return Settings(
        env="testing",
        debug=True,
        log_level="DEBUG",
        scraping={
            "request_timeout": 5,
            "max_retries": 1,
            "rate_limit_per_second": 10,
        },
        database={"database_url": "sqlite:///:memory:"},
    )
