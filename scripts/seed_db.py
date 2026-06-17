#!/usr/bin/env python3
"""Seed database with sample data for testing."""

import argparse
import random
from datetime import date, datetime, timedelta

from src.storage.database import init_db


def generate_sample_data(count: int = 100) -> list:
    """Generate sample hotel data for testing.

    Args:
        count: Number of records to generate

    Returns:
        List of sample records
    """
    hotels = [
        "Cinnamon Grand Colombo", "Shangri-La Colombo", "Hilton Colombo",
        "The Kingsbury", "Galle Face Hotel", "Mount Lavinia Hotel",
        "Cinnamon Lakeside", "Movenpick Colombo", "Jetwing Colombo Seven",
        "Taj Samudra", "Heritance Kandalama", "Earl's Regency",
        "Hotel Suisse", "Cinnamon Citadel", "Queen's Hotel",
        "Amaya Hills", "Fortaleza", "The Fortress Resort",
        "Jetwing Lighthouse", "Cinnamon Bentota Beach", "Heritance Ahungalla",
        "Cinnamon Lodge Habarana", "Jetwing Vil Uyana", "Cinnamon Wild Yala",
        "Jetwing Yala", "Cinnamon Bey", "Uga Bay", "Trinco Blu",
        "Anantara Peace Haven", "Weligama Bay Marriott",
    ]
    cities = ["Colombo", "Kandy", "Galle", "Negombo", "Nuwara Eliya",
              "Bentota", "Sigiriya", "Ella", "Mirissa", "Trincomalee"]
    sources = ["booking", "agoda", "expedia"]
    room_types = ["Standard", "Deluxe", "Suite", "Superior", "Executive"]

    records = []
    base_date = date.today().replace(day=1)

    for i in range(count):
        hotel = random.choice(hotels)
        city = random.choice(cities)
        source = random.choice(sources)

        # Random date within last 3 months
        days_offset = random.randint(0, 90)
        checkin = base_date + timedelta(days=days_offset)
        checkout = checkin + timedelta(days=random.randint(1, 7))

        record = {
            "hotel_name": hotel,
            "source": source,
            "city": city,
            "country": "Sri Lanka",
            "checkin_date": checkin,
            "checkout_date": checkout,
            "nightly_rate": round(random.uniform(50, 500), 2),
            "currency": random.choice(["USD", "LKR"]),
            "available_rooms": random.randint(0, 50),
            "occupancy_pct": round(random.uniform(40, 95), 1),
            "room_type": random.choice(room_types),
            "guest_score": round(random.uniform(6.0, 9.8), 1),
            "review_count": random.randint(10, 5000),
            "scraped_at": datetime.utcnow(),
            "url": f"https://www.{source}.com/hotel/{i}",
        }
        records.append(record)

    return records


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Seed database with sample data")
    parser.add_argument(
        "--init", action="store_true", help="Initialize database only"
    )
    parser.add_argument(
        "--seed", action="store_true", help="Seed with sample data"
    )
    parser.add_argument(
        "--count", type=int, default=100, help="Number of records to generate"
    )
    parser.add_argument(
        "--db-url", default=None, help="Database URL"
    )

    args = parser.parse_args()

    # Initialize database
    storage = init_db(args.db_url)
    print("Database initialized")

    if args.seed or not args.init:
        records = generate_sample_data(args.count)
        saved = storage.save(records)
        print(f"Seeded {saved} sample records")


if __name__ == "__main__":
    main()
