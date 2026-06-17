# Selector Maintenance Guide

## Overview

CSS selectors are the most fragile part of any web scraper. Websites change their HTML structure frequently, which breaks selectors and causes scraping failures.

## How Selectors Work

The scraper uses CSS selectors defined in `src/config/selectors.yaml` to locate data within HTML pages:

```yaml
booking:
  hotel_name: "div[data-testid='title']"
  hotel_price: "span[data-testid='price-and-discounted-price']"
```

## Common Selector Failure Patterns

### 1. Changed `data-testid` Attributes
```yaml
# OLD (broken)
hotel_name: "div[data-testid='title']"

# NEW (fixed)
hotel_name: "div[data-testid='property-title']"
```

### 2. Changed Class Names (CSS modules)
```yaml
# OLD (broken)
hotel_price: "span.sc-dWOrae"

# NEW (fixed)
hotel_price: "span.sc-kDnyCx"
```

### 3. Changed HTML Structure
```yaml
# OLD (broken)
hotel_rating: "div[data-testid='review-score'] div"

# NEW (fixed)
hotel_rating: "div[data-testid='review-score'] span"
```

### 4. Removed Elements
```yaml
# If element is removed entirely, may need to find alternative
# OLD
hotel_badge: "div.sc-bdnxRM"

# NEW - use different indicator
hotel_badge: "div[data-testid='property-card-badge']"
```

## How to Update Selectors

### Step 1: Identify the Problem

Check logs for parsing errors:
```bash
# Look for warnings about empty results
grep "No more results found\|Failed to parse" logs/scraper_*.log
```

### Step 2: Inspect the Website

1. Open the website in your browser
2. Right-click on the element you want to scrape
3. Select "Inspect" or "Inspect Element"
4. Look at the HTML structure

### Step 3: Test New Selectors

Use browser console to test:
```javascript
// Test in browser console
document.querySelector("div[data-testid='title']")
document.querySelectorAll("div[data-testid='property-card']").length
```

### Step 4: Update selectors.yaml

```yaml
booking:
  # Update the broken selector
  hotel_name: "div[data-testid='new-title-attribute']"
```

### Step 5: Test the Scraper

```bash
python -m src.main scrape --source booking --city Colombo --max-pages 1
```

## Selector Health Monitoring

### Automated Health Checks

The test suite includes selector health checks:

```bash
# Run selector tests
pytest tests/ -m selector_health -v
```

### Manual Health Check Script

```python
# quick_check.py
from src.scrapers import BookingScraper

scraper = BookingScraper()
html = scraper.fetch_page("https://www.booking.com/searchresults.html?ss=Colombo")

# Test selectors
soup = scraper.parser.parse_with_soup(html)
cards = soup.select("div[data-testid='property-card']")
print(f"Found {len(cards)} hotel cards")

if len(cards) == 0:
    print("WARNING: Selector may be broken!")
    # Try alternative selectors
    alt_cards = soup.select("[data-testid*='property']")
    print(f"Alternative found: {len(alt_cards)}")
```

## Best Practices

### 1. Use Stable Selectors

Prefer `data-testid` or `id` over class names:
```yaml
# Good - stable
div[data-testid='property-card']

# Risky - changes often
div.sc-jrAGrp.dhBPOk
```

### 2. Use Partial Attribute Matches

```yaml
# More resilient to minor changes
[data-testid*='property']      # Contains 'property'
[data-testid^='property']      # Starts with 'property'
[data-testid$='card']          # Ends with 'card'
```

### 3. Have Fallback Selectors

```python
# In parser code, try multiple selectors
for selector in ["div[data-testid='title']", "h3.title", ".hotel-name"]:
    element = soup.select_one(selector)
    if element:
        break
```

### 4. Monitor Selector Effectiveness

Track parse success rate:
```python
# Log warnings when parse rate drops
if len(results) == 0 and len(html) > 10000:
    logger.warning("Possible selector failure - page loaded but no results parsed")
```

## Selector Update Checklist

- [ ] Check logs for parse failures
- [ ] Inspect website HTML manually
- [ ] Update `selectors.yaml`
- [ ] Run scraper with `--max-pages 1` to test
- [ ] Run full test suite
- [ ] Update this documentation if patterns change

## Website-Specific Notes

### Booking.com
- Uses `data-testid` attributes (relatively stable)
- A/B tests different layouts
- Rate limits aggressive scraping

### Agoda.com
- Heavy JavaScript rendering
- Class names change frequently (CSS modules)
- Often requires Playwright

### Expedia.com
- Mix of static and dynamic content
- Has GraphQL API (more stable than HTML)
- Class names use utility patterns

### SLTDA (sltda.gov.lk)
- Static HTML (rarely changes)
- Government sites are more stable
- Table structures are consistent

### data.gov.lk
- CKAN API (very stable)
- HTML structure changes less frequently
- API preferred over HTML scraping
