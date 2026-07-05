"""Tests for junk record filtering."""

from src.utils.validators import filter_scraped_records, is_junk_record


class TestJunkFiltering:
    def test_rejects_unknown_hotel_name(self):
        assert is_junk_record(
            {
                "hotel_name": "Unknown",
                "source": "booking",
                "city": "Colombo",
                "location_verified": True,
            }
        )

    def test_rejects_lowercase_unknown(self):
        assert is_junk_record(
            {
                "hotel_name": "unknown",
                "source": "booking",
                "city": "Colombo",
                "location_verified": True,
            }
        )

    def test_rejects_datagovlk(self):
        assert is_junk_record(
            {
                "hotel_name": "Tourism Dataset",
                "source": "datagovlk",
                "city": "Colombo",
            }
        )

    def test_rejects_travel_without_verified_location(self):
        assert is_junk_record(
            {
                "hotel_name": "Some Hotel",
                "source": "booking",
                "city": "Galle",
                "location_verified": False,
            }
        )

    def test_keeps_valid_hotel(self):
        assert not is_junk_record(
            {
                "hotel_name": "Cinnamon Grand",
                "source": "booking",
                "city": "Colombo",
                "location_verified": True,
            }
        )

    def test_filter_batch(self):
        rows = [
            {"hotel_name": "Unknown", "source": "booking", "city": "Colombo", "location_verified": True},
            {
                "hotel_name": "Valid Hotel",
                "source": "agoda",
                "city": "kandy",
                "location_verified": True,
            },
        ]
        cleaned = filter_scraped_records(rows)
        assert len(cleaned) == 1
        assert cleaned[0]["city"] == "Kandy"
