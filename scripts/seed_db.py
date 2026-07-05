#!/usr/bin/env python3
"""Seed database with real Sri Lankan hotel data."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.sri_lanka_hotels import generate_real_hotel_records
from src.storage.database import init_db


def main():
    parser = argparse.ArgumentParser(description="Seed database with real hotel data")
    parser.add_argument("--init", action="store_true", help="Initialize database only")
    parser.add_argument("--seed", action="store_true", help="Seed with real hotel data")
    parser.add_argument("--count", type=int, default=250, help="Number of records")
    parser.add_argument("--db-url", default=None, help="Database URL")
    args = parser.parse_args()

    storage = init_db(args.db_url)
    print("Database initialized")

    if args.seed or not args.init:
        records = generate_real_hotel_records(args.count)
        saved = storage.save(records)
        print(f"Seeded {saved} real hotel records")


if __name__ == "__main__":
    main()
