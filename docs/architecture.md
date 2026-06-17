# Hotel Scraper - Architecture Documentation

## Overview

The Hotel Check-in Scraper is a production-grade web scraping system designed to collect hotel data from multiple sources (Booking.com, Agoda, Expedia, SLTDA, and data.gov.lk) to analyze which hotels have the most check-ins each month.

## System Architecture

```
                    ┌─────────────────────────────────────┐
                    │         CLI / Scheduler             │
                    │         (Entry Point)               │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │      Source Router                  │
                    │  (Booking/Agoda/Expedia/SLTDA/DataGov) │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     ┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
     │ HTTP Scraper    │  │ JS Scraper     │  │ API Client     │
     │ (requests)      │  │ (Playwright)   │  │ (CKAN/GraphQL) │
     └────────┬────────┘  └───────┬────────┘  └───────┬────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │      Parser Layer                   │
                    │  (HTML → Structured Data)          │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │    Validation Layer                 │
                    │  (Pydantic Models)                  │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     ┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
     │ CSV Storage     │  │ JSON Storage   │  │ Database       │
     │ (Beginner)      │  │ (Intermediate) │  │ (Production)   │
     └─────────────────┘  └────────────────┘  └────────────────┘
```

## Component Details

### 1. Scrapers Layer (`src/scrapers/`)

| Component | Purpose | Technology |
|-----------|---------|------------|
| `BaseScraper` | Abstract base with common functionality | requests, Playwright |
| `BookingScraper` | Booking.com hotel data | requests + Playwright fallback |
| `AgodaScraper` | Agoda.com hotel data | Playwright (JS-heavy) |
| `ExpediaScraper` | Expedia.com hotel data | Playwright + GraphQL API |
| `SLTDAScraper` | Government tourism stats | requests (static HTML) |
| `DataGovLkScraper` | Open data portal | CKAN API + HTML fallback |

### 2. Parser Layer (`src/parsers/`)

| Component | Purpose |
|-----------|---------|
| `BaseParser` | Abstract base with BeautifulSoup utilities |
| `HotelParser` | Source-specific hotel data extraction |
| `ReviewParser` | Hotel review extraction |

### 3. Storage Layer (`src/storage/`)

| Component | Use Case | Performance |
|-----------|----------|-------------|
| `CSVStorage` | Beginner, small datasets, human-readable | Slow for large data |
| `JSONStorage` | Nested data, API integration | Moderate |
| `DatabaseStorage` | Production, large datasets, analytics | Fast with indexes |

### 4. Utilities Layer (`src/utils/`)

| Component | Purpose |
|-----------|---------|
| `SessionManager` | HTTP sessions with retry, proxy, UA rotation |
| `RateLimiter` | Token bucket rate limiting |
| `ProxyRotator` | Proxy pool with health tracking |
| `UserAgentRotator` | Randomized user agent strings |
| `Retry` | Exponential backoff retry logic |
| `Validators` | Pydantic data validation |

### 5. Monitoring Layer (`src/monitoring/`)

| Component | Purpose |
|-----------|---------|
| `Logger` | Structured logging with loguru |
| `Metrics` | Prometheus metrics collection |

## Data Flow

### Scraping Flow
```
1. CLI receives command
2. Source router selects appropriate scraper
3. Scraper builds search URL
4. Rate limiter checks if request is allowed
5. Session manager makes HTTP request
6. If HTML: Parser extracts data
   If API: JSON response parsed directly
7. Data validated with Pydantic models
8. Valid records saved to storage
9. Metrics recorded
10. Results returned
```

### Analytics Flow
```
1. Query received (top hotels, monthly stats)
2. Storage layer executes query
3. For CSV/JSON: In-memory aggregation
   For Database: SQL aggregation
4. Results formatted and returned
```

## Design Decisions

### Why Multiple Scrapers?

Each source has unique characteristics:
- **Booking.com**: Mix of static and dynamic content
- **Agoda**: Heavy JavaScript, requires browser automation
- **Expedia**: Has GraphQL API for reliable access
- **SLTDA**: Static government pages with tables
- **data.gov.lk**: CKAN API for structured data

### Why Multiple Storage Backends?

Progressive complexity approach:
- **Beginners** can use CSV and inspect in Excel
- **Intermediate** users get JSON for API integration
- **Production** uses PostgreSQL for performance and analytics

### Rate Limiting Strategy

Token bucket algorithm provides:
- Burst handling for quick requests
- Smooth limiting for sustained scraping
- Adaptive slowdown on errors (429 responses)

## Scaling Considerations

### Vertical Scaling
- Increase `CONCURRENT_REQUESTS`
- Use more powerful proxies
- Upgrade to faster database

### Horizontal Scaling
- Run multiple scraper instances with different city assignments
- Use message queue (Redis/RabbitMQ) for task distribution
- Shard database by city or date range

## Security Considerations

1. **Respect robots.txt**: Check before scraping
2. **Rate limiting**: Never exceed reasonable request rates
3. **User-Agent rotation**: Identify as scraper honestly
4. **No CAPTCHA bypass**: Stop when challenged
5. **Data retention**: Only store what's needed
6. **Encryption**: Use HTTPS for all requests

## Monitoring & Alerting

### Key Metrics
- `scraper_requests_total`: Total HTTP requests
- `scraper_errors_total`: Error count by type
- `scraper_hotels_total`: Hotels successfully scraped
- `scraper_request_duration_seconds`: Request latency

### Alerts
- Error rate > 10%: Check selectors/site changes
- No data for 24h: Scheduler failure
- Rate limit hits: Reduce request frequency
