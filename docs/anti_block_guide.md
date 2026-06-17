# Anti-Blocking Guide

## Overview

Web scraping often triggers anti-bot protections. This guide explains how to avoid blocks while maintaining ethical scraping practices.

## Why Scrapers Get Blocked

1. **Too many requests** - Sending requests too quickly
2. **Pattern detection** - Same IP, same headers, same timing
3. **Missing browser signals** - No JavaScript execution, no cookies
4. **Bot fingerprints** - Headless browser detection
5. **CAPTCHA triggers** - Suspicious behavior patterns

## Protection Strategies (Implemented)

### 1. Rate Limiting

```yaml
# .env
RATE_LIMIT_PER_SECOND=0.5  # Max 1 request per 2 seconds
```

Token bucket algorithm provides:
- Sustainable request rates
- Burst handling when needed
- Automatic slowdown on errors

### 2. User-Agent Rotation

```python
# Automatically rotates between real browser UAs
headers = {"User-Agent": get_random_user_agent()}
```

Rotates between:
- Chrome (Windows/Mac/Linux)
- Firefox
- Safari
- Edge

### 3. Proxy Rotation

```yaml
# .env
PROXY_ROTATION=true
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
```

Features:
- Round-robin, random, weighted strategies
- Health tracking per proxy
- Automatic failover
- Response time monitoring

### 4. Session Management

```python
# Fresh sessions with:
# - Random User-Agent
# - Realistic headers (Accept, Accept-Language, etc.)
# - Cookie handling
# - Proxy configuration
```

### 5. Retry with Backoff

```python
@with_retry(max_retries=3, base_delay=2)
def fetch_page(url):
    # Automatically retries with exponential backoff
    # 2s, 4s, 8s delays between retries
```

### 6. Playwright for JavaScript Sites

```python
# For JS-heavy sites like Agoda:
html = scraper.fetch_page_playwright(
    url,
    wait_for=".PropertyCard",  # Wait for content to load
    timeout=45000,
)
```

Simulates real browser:
- Executes JavaScript
- Handles lazy loading
- Processes cookies
- Renders dynamic content

## Ethical Scraping Checklist

### DO:
- ✅ Check `robots.txt` before scraping
- ✅ Use reasonable rate limits (1 req per 2-5 seconds)
- ✅ Identify yourself in User-Agent
- ✅ Respect `noindex` and `nofollow` directives
- ✅ Stop when you see CAPTCHAs
- ✅ Cache results to avoid duplicate requests
- ✅ Use official APIs when available

### DON'T:
- ❌ Scrape faster than a human could browse
- ❌ Bypass CAPTCHAs or login walls
- ❌ Scrape personal data
- ❌ DDoS the website
- ❌ Ignore robots.txt
- ❌ Use scraped data commercially without permission

## Detection Signals We Avoid

| Signal | How We Avoid It |
|--------|----------------|
| Same IP | Proxy rotation |
| Same User-Agent | UA rotation |
| Perfect timing | Random delays |
| No JavaScript | Playwright for JS sites |
| Missing cookies | Session persistence |
| Headless detection | Playwright stealth |

## When You Get Blocked

### Signs of Blocking:
- 403 Forbidden responses
- 429 Too Many Requests
- CAPTCHA pages
- Redirects to login
- Empty responses
- Different HTML structure

### What to Do:

1. **Stop immediately** - Don't make it worse
2. **Check the response** - Look at the HTML/error
3. **Increase delays** - Reduce rate limit
4. **Switch proxies** - Use different IP
5. **Try Playwright** - If not already using it
6. **Wait and retry** - Some blocks are temporary

### Emergency Recovery:

```python
# Increase delays
settings.RATE_LIMIT_PER_SECOND = 0.2  # 1 per 5 seconds

# Switch to Playwright
scraper.scrape(..., use_playwright=True)

# Use fresh session
scraper.session_manager.refresh_session()

# Add more proxies
scraper.proxy_rotator.add_proxy("http://new-proxy:8080")
```

## Source-Specific Notes

### Booking.com
- Moderate anti-bot protection
- `data-testid` attributes suggest they expect scraping
- Respects reasonable rate limits
- Playwright usually not needed for search

### Agoda.com
- Heavy anti-bot protection
- Requires JavaScript execution
- Playwright recommended
- More aggressive blocking

### Expedia.com
- Moderate protection
- GraphQL API is more reliable than HTML
- Use API when possible

### SLTDA / data.gov.lk
- No anti-bot protection
- Government public data
- Static HTML or API
- Can scrape normally

## Monitoring for Blocks

The scraper tracks:
- HTTP status codes (403, 429, etc.)
- Response sizes (sudden drops indicate blocks)
- Parse success rates (0 results = possible block)
- Error rates by source

Check metrics:
```bash
# View error rates
python -m src.main stats

# Check recent logs
tail -f logs/scraper_*.log | grep -i "error\|block\|429\|403"
```

## Legal Considerations

This scraper is designed for **educational purposes**:
- SLTDA and data.gov.lk data is public
- Booking.com/Agoda/Expedia data requires care
- Always check Terms of Service
- Consider using official APIs or affiliate programs
- Don't republish data without permission

## Testing Your Setup

Before production scraping:

```bash
# Test with 1 page
python -m src.main scrape --source booking --city Colombo --max-pages 1

# Check for blocks
grep -i "captcha\|blocked\|403\|429" logs/scraper_*.log

# Gradually increase
python -m src.main scrape --source booking --city Colombo --max-pages 3
```
