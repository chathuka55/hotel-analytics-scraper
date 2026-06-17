"""Tests for hotel and review parsers."""

import pytest
from datetime import date

from src.parsers.hotel_parser import HotelParser
from src.parsers.review_parser import ReviewParser
from src.utils.validators import HotelCheckin


class TestHotelParser:
    """Test cases for HotelParser."""

    def test_booking_parser_basic(self, mock_booking_html):
        """Test basic Booking.com HTML parsing."""
        parser = HotelParser("booking")
        results = parser.parse_search_results(
            html=mock_booking_html,
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        assert len(results) == 2
        assert results[0]["hotel_name"] == "Cinnamon Grand Colombo"
        assert results[1]["hotel_name"] == "Shangri-La Colombo"

    def test_booking_parser_data_extraction(self, mock_booking_html):
        """Test that all fields are extracted correctly."""
        parser = HotelParser("booking")
        results = parser.parse_search_results(
            html=mock_booking_html,
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        hotel = results[0]
        assert hotel["hotel_name"] == "Cinnamon Grand Colombo"
        assert hotel["source"] == "booking"
        assert hotel["city"] == "Colombo"
        assert hotel["nightly_rate"] == 150.0
        assert hotel["currency"] == "USD"
        assert hotel["guest_score"] == 8.7
        assert hotel["review_count"] == 1250

    def test_agoda_parser(self, mock_agoda_html):
        """Test Agoda HTML parsing."""
        parser = HotelParser("agoda")
        results = parser.parse_search_results(
            html=mock_agoda_html,
            city="Dambulla",
            checkin_date=date(2026, 8, 1),
            checkout_date=date(2026, 8, 5),
        )

        assert len(results) == 1
        assert results[0]["hotel_name"] == "Heritance Kandalama"

    def test_parser_validation(self, mock_booking_html):
        """Test that parsed results can be validated."""
        parser = HotelParser("booking")
        results = parser.parse_search_results(
            html=mock_booking_html,
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )

        validation = parser.validate_batch(results)
        assert validation.validated > 0

    def test_parser_empty_html(self):
        """Test parsing empty HTML."""
        parser = HotelParser("booking")
        results = parser.parse_search_results(
            html="<html><body></body></html>",
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )
        assert len(results) == 0

    def test_parser_invalid_html(self):
        """Test parsing malformed HTML."""
        parser = HotelParser("booking")
        results = parser.parse_search_results(
            html="<not-valid-html>>><",
            city="Colombo",
            checkin_date=date(2026, 7, 15),
            checkout_date=date(2026, 7, 18),
        )
        assert len(results) == 0

    def test_score_parsing(self):
        """Test various score formats."""
        parser = HotelParser("booking")

        assert parser._parse_score("8.5") == 8.5
        assert parser._parse_score("8.5/10") == 8.5
        assert parser._parse_score("4.5/5") == 9.0
        assert parser._parse_score("85%") == 8.5
        assert parser._parse_score("Excellent 9.2") == 9.2
        assert parser._parse_score("") == 0.0
        assert parser._parse_score("invalid") == 0.0

    def test_hotel_detail_parsing(self, mock_booking_html):
        """Test hotel detail page parsing."""
        parser = HotelParser("booking")
        detail = parser.parse_hotel_detail(
            html=mock_booking_html,
            hotel_url="https://booking.com/hotel/123",
        )

        assert detail["url"] == "https://booking.com/hotel/123"
        assert detail["source"] == "booking"


class TestReviewParser:
    """Test cases for ReviewParser."""

    def test_review_date_parsing(self):
        """Test various date formats."""
        parser = ReviewParser("booking")

        assert parser._parse_review_date("July 15, 2026") == "2026-07-15"
        assert parser._parse_review_date("15 July 2026") == "2026-07-15"
        assert parser._parse_review_date("2026-07-15") == "2026-07-15"
        assert parser._parse_review_date("") is None
        assert parser._parse_review_date("invalid") is None

    def test_review_score_parsing(self):
        """Test review score parsing."""
        parser = ReviewParser("booking")

        assert parser._parse_review_score("8.5") == 8.5
        assert parser._parse_review_score("4.5/5") == 9.0
        assert parser._parse_review_score("85%") == 8.5
        assert parser._parse_review_score("") == 0.0

    def test_empty_reviews(self):
        """Test parsing page with no reviews."""
        parser = ReviewParser("booking")
        result = parser.parse_hotel_detail(
            html="<html><body></body></html>",
            hotel_url="https://example.com",
        )

        assert result["total_reviews"] == 0
        assert result["reviews"] == []
        assert result["summary"]["average_score"] == 0.0

    def test_summary_calculation(self):
        """Test review summary statistics."""
        parser = ReviewParser("booking")
        reviews = [
            {"score": 8.0, "text": "Good"},
            {"score": 9.0, "text": "Great"},
            {"score": 7.0, "text": "OK"},
        ]
        summary = parser._calculate_summary(reviews)

        assert summary["average_score"] == 8.0
        assert summary["total_reviews"] == 3


class TestPydanticValidation:
    """Test Pydantic model validation."""

    def test_valid_hotel_checkin(self, sample_hotel_data):
        """Test valid data creates model successfully."""
        hotel = HotelCheckin(**sample_hotel_data)
        assert hotel.hotel_name == "Cinnamon Grand Colombo"
        assert hotel.guest_score == 8.7
        assert hotel.length_of_stay == 3

    def test_invalid_dates(self, sample_hotel_data):
        """Test that checkout before checkin raises error."""
        data = sample_hotel_data.copy()
        data["checkin_date"] = date(2026, 7, 18)
        data["checkout_date"] = date(2026, 7, 15)

        with pytest.raises(ValueError):
            HotelCheckin(**data)

    def test_missing_required_fields(self):
        """Test that missing required fields raise error."""
        with pytest.raises(ValueError):
            HotelCheckin(source="booking")

    def test_currency_normalization(self, sample_hotel_data):
        """Test currency code normalization."""
        data = sample_hotel_data.copy()
        data["currency"] = "US$"
        hotel = HotelCheckin(**data)
        assert hotel.currency == "USD"

    def test_score_bounds(self, sample_hotel_data):
        """Test score validation rejects out-of-bounds values."""
        data = sample_hotel_data.copy()
        data["guest_score"] = 15.0  # Above max

        # Pydantic v2 should raise validation error for out-of-bounds
        with pytest.raises(ValueError):
            HotelCheckin(**data)

    def test_csv_export(self, sample_hotel_data):
        """Test CSV row export."""
        hotel = HotelCheckin(**sample_hotel_data)
        row = hotel.to_csv_row()

        assert row["hotel_name"] == "Cinnamon Grand Colombo"
        assert "checkin_date" in row
        assert "scraped_at" in row
