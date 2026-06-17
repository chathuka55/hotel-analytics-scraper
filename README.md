#  Hotel Check-in Data Scraper — Complete Learning Project

> **Educational Purpose Only** — Respects robots.txt, rate limits, and site ToS.
> This project is designed to teach web scraping architecture, not to bypass protections.

---

##  Mind Map — Beginner → Production

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │         HOTEL CHECK-IN WEB SCRAPER SYSTEM                  │
                    │     (Booking.com | Agoda | Expedia | SLTDA | data.gov.lk)  │
                    └─────────────────────────────────────────────────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          ▼                               ▼                               ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   BEGINNER LEVEL    │     │  INTERMEDIATE LEVEL │     │   ADVANCED LEVEL    │
│   (Weeks 1-2)       │     │  (Weeks 3-4)        │     │  (Weeks 5-8+)       │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ • requests + BS4    │     │ • Playwright/Selenium│    │ • Async scraping     │
│ • Static gov sites  │     │ • Proxy rotation     │     │ • Docker/K8s         │
│ • Single-threaded   │     │ • Session mgmt       │     │ • Message queues     │
│ • CSV output        │     │ • Rate limiting      │     │ • DB (Postgres)      │
│ • Basic error hand. │ ───►│ • Logging            │ ───►│ • CI/CD pipeline     │
│ • 1 scraper file    │     │ • Modular structure  │     │ • Monitoring/Alert   │
│ • No config         │     │ • Config files       │     │ • Distributed crawl  │
│ • Manual run        │     │ • Retry logic        │     │ • API layer          │
│ • 10-50 reqs        │     │ • 500-2K reqs        │     │ • 10K+ reqs/day      │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
          │                          │                            │
          └──────────────────────────┼────────────────────────────┘
                                     ▼
                    ┌─────────────────────────────────────┐
                    │         TESTING STRATEGY             │
                    ├─────────────────────────────────────┤
                    │ • Unit tests (mock responses)       │
                    │ • Integration tests (live URLs)     │
                    │ • Selector health checks            │
                    │ • Data quality validation           │
                    │ • Performance benchmarks            │
                    │ • Regression test suite             │
                    └─────────────────────────────────────┘
```

---

##  Project Structure

```
hotel-scraper/
├── README.md
├── requirements.txt
├── setup.py
├── Makefile
├── .env.example
├── .gitignore
├── pyproject.toml
│
├── src/
│   ├── __init__.py
│   ├── main.py                       # Entry point (CLI)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic settings
│   │   └── selectors.yaml            # CSS/XPath selectors
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract base scraper
│   │   ├── booking.py                # Booking.com scraper
│   │   ├── agoda.py                  # Agoda.com scraper
│   │   ├── expedia.py                # Expedia.com scraper
│   │   ├── sltda.py                  # SLTDA gov scraper
│   │   └── datagovlk.py              # data.gov.lk scraper
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract parser
│   │   ├── hotel_parser.py           # Hotel data parser
│   │   └── review_parser.py          # Review data parser
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract storage
│   │   ├── csv_storage.py            # CSV writer
│   │   ├── json_storage.py           # JSON writer
│   │   └── database.py               # SQLite/Postgres
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── proxies.py                # Proxy rotation
│   │   ├── rate_limiter.py           # Rate limiting
│   │   ├── retry.py                  # Retry with backoff
│   │   ├── user_agents.py            # UA rotation
│   │   ├── session.py                # Session manager
│   │   └── validators.py             # Data validators
│   │
│   └── monitoring/
│       ├── __init__.py
│       ├── logger.py                 # Structured logging
│       └── metrics.py                # Prometheus metrics
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_booking_scraper.py
│   ├── test_agoda_scraper.py
│   ├── test_expedia_scraper.py
│   ├── test_sltda_scraper.py
│   ├── test_datagovlk_scraper.py
│   ├── test_parsers.py
│   ├── test_storage.py
│   ├── test_rate_limiter.py
│   ├── test_proxies.py
│   └── fixtures/                     # Mock HTML/JSON
│       ├── booking_search.html
│       ├── agoda_search.html
│       └── sltda_report.html
│
├── scripts/
│   ├── run_all.sh                    # Run all scrapers
│   ├── docker_build.sh               # Docker build
│   └── seed_db.py                    # DB initialization
│
├── data/
│   ├── raw/                          # Raw scraped data
│   └── processed/                    # Cleaned/aggregated
│
└── docs/
    ├── architecture.md
    ├── selector_maintenance.md
    └── anti_block_guide.md
```

---

##  Architecture Overview

```
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐
│  CLI     │──►│ Scheduler│──►│ Scrapers │──►│ Parsers   │
│ (main.py)│   │ (cron/   │   │ (src/    │   │ (src/     │
│          │   │  APSched)│   │  scrapers)│  │  parsers) │
└─────────┘   └──────────┘   └──────────┘   └───────────┘
                                               │
                                      ┌────────▼────────┐
                                      │    Storage      │
                                      │ (CSV/JSON/DB)  │
                                      └────────┬────────┘
                                               │
                                      ┌────────▼────────┐
                                      │   Analytics     │
                                      │ (Most check-ins │
                                      │  per month)     │
                                      └─────────────────┘
```

---

##  Python Libraries Used

| Library            | Purpose                         | Level       |
|--------------------|----------------------------------|-------------|
| `requests`         | HTTP requests (static sites)     | Beginner    |
| `beautifulsoup4`   | HTML parsing                    | Beginner    |
| `lxml`             | Fast XML/HTML parsing           | Beginner    |
| `playwright`       | Browser automation              | Intermediate|
| `selenium`         | Browser automation (alt)        | Intermediate|
| `aiohttp`          | Async HTTP requests             | Advanced    |
| `scrapy`           | Production scraping framework   | Advanced    |
| `pydantic`         | Data validation/settings        | All levels  |
| `pandas`           | Data analysis                   | Intermediate|
| `sqlalchemy`       | Database ORM                    | Advanced    |
| `loguru`           | Structured logging              | All levels  |
| `pytest`           | Testing                         | All levels  |
| `tenacity`         | Retry logic                     | Intermediate|
| `docker`           | Containerization                | Advanced    |
| `prometheus_client`| Metrics                         | Advanced    |
| `fastapi`          | API layer                       | Advanced    |

---

##  Data Model: Hotel Check-ins

```python
class HotelCheckin(BaseModel):
    hotel_name: str
    source: str               # booking.com, agoda, expedia, sltda
    city: str
    country: str              # Default: "Sri Lanka"
    checkin_date: date
    checkout_date: date
    nightly_rate: float       # In USD or LKR
    currency: str
    available_rooms: int
    occupancy_pct: float      # Derived: check-ins / total rooms
    room_type: str
    guest_score: float        # 0-10
    review_count: int
    scraped_at: datetime
    url: str
```

---

##  Testing Strategy

| Test Type          | What It Covers                         | Tools                 |
|--------------------|----------------------------------------|-----------------------|
| Unit Tests         | Parser logic, validators, utils        | pytest, mock         |
| Integration Tests  | Full scrape → parse → store pipeline   | pytest, responses    |
| Selector Tests     | CSS/XPath still match current HTML     | pytest + live check  |
| Data Quality       | Schema validation, missing fields      | pydantic, pandas     |
| Performance        | Requests/sec, memory usage             | pytest-benchmark     |
| Regression         | No breakage when adding features       | pytest-snapshot      |

---

##  Getting Started

```bash
# Clone & setup
cd hotel-scraper
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers
playwright install chromium

# Run the scraper
python src/main.py --source booking --city Colombo --checkin 2026-07-01 --checkout 2026-07-03

# Run tests
pytest tests/ -v --cov=src

# Run all scrapers
bash scripts/run_all.sh
```

---

##  Legal & Ethical Notes

This project is for **educational purposes only**. Before scraping any site:

1. ✅ **Check `robots.txt`** — e.g., `https://www.booking.com/robots.txt`
2. ✅ **Rate limit** — max 1 request per 3-5 seconds
3. ✅ **Identify yourself** — use a descriptive User-Agent
4. ✅ **Don't bypass CAPTCHAs** — if blocked, stop
5. ✅ **Government data** (SLTDA, data.gov.lk) is **public & legal**
6. ❌ **Don't republish** scraped data without permission
7. ❌ **Don't use for commercial purposes** without license

