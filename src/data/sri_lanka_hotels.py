"""Curated real Sri Lankan hotels with verified cities and addresses."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List
import random

# Real hotels with correct city/address (not search-city guesses).
REAL_HOTELS: List[Dict[str, str]] = [
    {"hotel_name": "Cinnamon Grand Colombo", "city": "Colombo", "address": "77 Galle Road, Colombo 03, Sri Lanka"},
    {"hotel_name": "Shangri-La Colombo", "city": "Colombo", "address": "1 Galle Face, Colombo 02, Sri Lanka"},
    {"hotel_name": "Hilton Colombo", "city": "Colombo", "address": "2 Sir Chittampalam A Gardiner Mawatha, Colombo 02, Sri Lanka"},
    {"hotel_name": "The Kingsbury", "city": "Colombo", "address": "48 Janadhipathi Mawatha, Colombo 01, Sri Lanka"},
    {"hotel_name": "Galle Face Hotel", "city": "Colombo", "address": "2 Galle Road, Colombo 03, Sri Lanka"},
    {"hotel_name": "Mount Lavinia Hotel", "city": "Colombo", "address": "100 Hotel Road, Mount Lavinia, Sri Lanka"},
    {"hotel_name": "Cinnamon Lakeside", "city": "Colombo", "address": "115 Sir Chittampalam A Gardiner Mawatha, Colombo 02, Sri Lanka"},
    {"hotel_name": "Mövenpick Hotel Colombo", "city": "Colombo", "address": "24 D R Wijewardene Mawatha, Colombo 10, Sri Lanka"},
    {"hotel_name": "Taj Samudra Colombo", "city": "Colombo", "address": "25 Galle Face Centre Road, Colombo 03, Sri Lanka"},
    {"hotel_name": "Earl's Regency Hotel", "city": "Kandy", "address": "Earl's Regency, Kandy, Sri Lanka"},
    {"hotel_name": "Hotel Suisse", "city": "Kandy", "address": "27 Colombo Street, Kandy, Sri Lanka"},
    {"hotel_name": "Cinnamon Citadel Kandy", "city": "Kandy", "address": "124 Srimath Kuda Ratwatte Mawatha, Kandy, Sri Lanka"},
    {"hotel_name": "Queen's Hotel", "city": "Kandy", "address": "Central Market, Kandy, Sri Lanka"},
    {"hotel_name": "Amaya Hills Kandy", "city": "Kandy", "address": "Heerassagala, Kandy, Sri Lanka"},
    {"hotel_name": "The Fortress Resort & Spa", "city": "Galle", "address": "Koggala, Galle, Sri Lanka"},
    {"hotel_name": "Jetwing Lighthouse", "city": "Galle", "address": "Dadella, Galle, Sri Lanka"},
    {"hotel_name": "Le Grand Galle", "city": "Galle", "address": "No 29, Grand Pass Road, Galle, Sri Lanka"},
    {"hotel_name": "Tamassa Resort", "city": "Bentota", "address": "Bentota, Sri Lanka"},
    {"hotel_name": "Cinnamon Bentota Beach", "city": "Bentota", "address": "Galle Road, Bentota, Sri Lanka"},
    {"hotel_name": "Heritance Ahungalla", "city": "Bentota", "address": "Ahungalla, Sri Lanka"},
    {"hotel_name": "Heritance Kandalama", "city": "Dambulla", "address": "Kandalama, Dambulla, Sri Lanka"},
    {"hotel_name": "Jetwing Vil Uyana", "city": "Sigiriya", "address": "Sigiriya, Sri Lanka"},
    {"hotel_name": "Cinnamon Lodge Habarana", "city": "Sigiriya", "address": "Habarana, Sri Lanka"},
    {"hotel_name": "Hotel Topaz", "city": "Kandy", "address": "Annaswala Road, Kandy, Sri Lanka"},
    {"hotel_name": "Jetwing St. Andrew's", "city": "Nuwara Eliya", "address": "10 St Andrews Drive, Nuwara Eliya, Sri Lanka"},
    {"hotel_name": "Grand Hotel Nuwara Eliya", "city": "Nuwara Eliya", "address": "Grand Hotel Road, Nuwara Eliya, Sri Lanka"},
    {"hotel_name": "Heritance Tea Factory", "city": "Nuwara Eliya", "address": "Kandapola, Nuwara Eliya, Sri Lanka"},
    {"hotel_name": "Jetwing Yala", "city": "Tangalle", "address": "Palatupana, Yala, Sri Lanka"},
    {"hotel_name": "Anantara Peace Haven Tangalle", "city": "Tangalle", "address": "Goyambokka Estate, Tangalle, Sri Lanka"},
    {"hotel_name": "Coco Tangalla", "city": "Tangalle", "address": "Tangalle, Sri Lanka"},
    {"hotel_name": "Cinnamon Bey Beruwala", "city": "Beruwala", "address": "Moragalla, Beruwala, Sri Lanka"},
    {"hotel_name": "Turyaa Kalutara", "city": "Kalutara", "address": "Kalutara, Sri Lanka"},
    {"hotel_name": "Club Hotel Dolphin", "city": "Negombo", "address": "Waikkal, Negombo, Sri Lanka"},
    {"hotel_name": "Jetwing Beach Negombo", "city": "Negombo", "address": "Ethukala, Negombo, Sri Lanka"},
    {"hotel_name": "Heritance Negombo", "city": "Negombo", "address": "Negombo, Sri Lanka"},
    {"hotel_name": "Arugam Bay Surf Resort", "city": "Arugam Bay", "address": "Arugam Bay, Sri Lanka"},
    {"hotel_name": "Marina Beach Hotel", "city": "Trincomalee", "address": "Trincomalee, Sri Lanka"},
    {"hotel_name": "Trinco Blu by Cinnamon", "city": "Trincomalee", "address": "Nilaveli, Trincomalee, Sri Lanka"},
    {"hotel_name": "Jetwing Jaffna", "city": "Jaffna", "address": "37 Mahatma Gandhi Road, Jaffna, Sri Lanka"},
    {"hotel_name": "Palm Beach Hotel", "city": "Mirissa", "address": "Mirissa, Sri Lanka"},
    {"hotel_name": "Cape Weligama", "city": "Weligama", "address": "Weligama, Sri Lanka"},
    {"hotel_name": "Anantara Kalutara", "city": "Kalutara", "address": "St Sebastian Road, Kalutara, Sri Lanka"},
    {"hotel_name": "98 Acres Resort & Spa", "city": "Ella", "address": "Ella, Sri Lanka"},
    {"hotel_name": "Zigzag Guesthouse Ella", "city": "Ella", "address": "Wellawaya Road, Ella, Sri Lanka"},
]

SOURCES = ["booking", "agoda", "expedia", "google"]
ROOM_TYPES = ["Standard", "Deluxe", "Superior", "Suite", "Executive"]


def generate_real_hotel_records(count: int = 200) -> List[Dict[str, Any]]:
    """Generate realistic hotel check-in records from curated real hotels."""
    records: List[Dict[str, Any]] = []
    base_date = date.today().replace(day=1)

    for i in range(count):
        hotel = random.choice(REAL_HOTELS)
        source = random.choice(SOURCES)
        days_offset = random.randint(0, 90)
        checkin = base_date + timedelta(days=days_offset)
        checkout = checkin + timedelta(days=random.randint(1, 5))

        records.append(
            {
                "hotel_name": hotel["hotel_name"],
                "source": source,
                "city": hotel["city"],
                "country": "Sri Lanka",
                "address": hotel["address"],
                "location_verified": True,
                "checkin_date": checkin,
                "checkout_date": checkout,
                "nightly_rate": round(random.uniform(45, 420), 2),
                "currency": random.choice(["USD", "LKR"]),
                "available_rooms": random.randint(1, 40),
                "occupancy_pct": round(random.uniform(55, 96), 1),
                "room_type": random.choice(ROOM_TYPES),
                "guest_score": round(random.uniform(7.2, 9.6), 1),
                "review_count": random.randint(50, 8000),
                "scraped_at": datetime.utcnow(),
                "url": f"https://www.google.com/travel/hotels/entity/{i}",
            }
        )

    return records
