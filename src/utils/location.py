"""City normalization and extraction from scraped location text."""

import re
from typing import Dict, List, Optional, Set, Tuple

# Canonical Sri Lankan cities used across all scrapers.
SRI_LANKAN_CITIES: List[str] = [
    "Colombo",
    "Kandy",
    "Galle",
    "Negombo",
    "Nuwara Eliya",
    "Bentota",
    "Sigiriya",
    "Ella",
    "Mirissa",
    "Trincomalee",
    "Jaffna",
    "Anuradhapura",
    "Dambulla",
    "Hikkaduwa",
    "Unawatuna",
    "Matara",
    "Polonnaruwa",
    "Kalutara",
    "Beruwala",
    "Arugam Bay",
    "Tangalle",
    "Weligama",
    "Ratnapura",
    "Badulla",
    "Batticaloa",
]

# Aliases and sub-areas mapped to canonical city names.
CITY_ALIASES: Dict[str, str] = {
    "colombo city": "Colombo",
    "colombo 01": "Colombo",
    "colombo 02": "Colombo",
    "colombo 03": "Colombo",
    "colombo 04": "Colombo",
    "colombo 05": "Colombo",
    "colombo 06": "Colombo",
    "colombo 07": "Colombo",
    "colombo 08": "Colombo",
    "colombo 09": "Colombo",
    "colombo 10": "Colombo",
    "colombo 11": "Colombo",
    "colombo 12": "Colombo",
    "colombo 13": "Colombo",
    "colombo 14": "Colombo",
    "colombo 15": "Colombo",
    "fort": "Colombo",
    "bambalapitiya": "Colombo",
    "wellawatta": "Colombo",
    "dehiwala": "Colombo",
    "mount lavinia": "Colombo",
    "mt lavinia": "Colombo",
    "nugegoda": "Colombo",
    "kotte": "Colombo",
    "sri jayawardenepura": "Colombo",
    "kandy city": "Kandy",
    "peradeniya": "Kandy",
    "galle fort": "Galle",
    "unawatuna": "Unawatuna",
    "hikkaduwa": "Hikkaduwa",
    "nuwara eliya": "Nuwara Eliya",
    "nuwaraeliya": "Nuwara Eliya",
    "little adams peak": "Ella",
    "arugam bay": "Arugam Bay",
    "trinco": "Trincomalee",
    "anuradhapura": "Anuradhapura",
    "polonnaruwa": "Polonnaruwa",
    "dambulla": "Dambulla",
    "sigiriya": "Sigiriya",
    "habarana": "Sigiriya",
    "mirissa": "Mirissa",
    "weligama": "Weligama",
    "matara": "Matara",
    "tangalle": "Tangalle",
    "beruwala": "Beruwala",
    "bentota": "Bentota",
    "kalutara": "Kalutara",
    "negombo": "Negombo",
    "jaffna": "Jaffna",
    "batticaloa": "Batticaloa",
    "badulla": "Badulla",
    "ratnapura": "Ratnapura",
    "ella": "Ella",
}

for city in SRI_LANKAN_CITIES:
    CITY_ALIASES.setdefault(city.lower(), city)

_CITY_MATCH_CACHE: Dict[str, Set[str]] = {}

# Street names that contain city names but are NOT the hotel city.
_STREET_FALSE_POSITIVES = re.compile(
    r"galle\s+(road|face|lane|street)|galle\s+rd",
    re.IGNORECASE,
)


def normalize_city(name: str) -> str:
    """Normalize a city name to its canonical form."""
    if not name:
        return ""

    key = name.strip().lower()
    if key in CITY_ALIASES:
        return CITY_ALIASES[key]

    return name.strip().title()


def _match_city_in_text(text: str) -> str:
    """Find a Sri Lankan city mentioned in free text (no search fallback)."""
    if not text:
        return ""

    lowered = text.lower()
    if _STREET_FALSE_POSITIVES.search(lowered) and "colombo" not in lowered:
        # "Galle Road, Colombo" handled by comma parsing below
        pass

    matches: List[tuple[int, str]] = []
    for alias, canonical in CITY_ALIASES.items():
        if len(alias) < 3:
            continue
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, lowered):
            matches.append((len(alias), canonical))

    if matches:
        matches.sort(reverse=True)
        best = matches[0][1]
        # Prefer Colombo when text is clearly a Colombo street address
        if best == "Galle" and re.search(
            r"galle\s+(road|face|lane|street|rd)\b.*\bcolombo\b", lowered
        ):
            return "Colombo"
        if best == "Galle" and re.search(
            r"\bcolombo\b", lowered
        ) and _STREET_FALSE_POSITIVES.search(lowered):
            return "Colombo"
        return best

    parts = [p.strip() for p in text.split(",") if p.strip()]
    for part in reversed(parts):
        part_key = part.lower()
        if part_key in CITY_ALIASES:
            return CITY_ALIASES[part_key]

    return ""


def parse_city_from_text(text: str) -> str:
    """Parse a canonical city from arbitrary text without search-city fallback."""
    return _match_city_in_text(text)


def extract_city_from_location(
    location_text: str, search_city: str = ""
) -> str:
    """Derive city from address; optional search_city only when text is empty."""
    parsed = _match_city_in_text(location_text)
    if parsed:
        return parsed
    if not location_text and search_city:
        return normalize_city(search_city)
    return ""


def extract_city_from_url(url: str) -> str:
    """Try to infer city from hotel URL path segments."""
    if not url:
        return ""

    slug = url.lower()
    slug = re.sub(r"[^a-z0-9\-_/]", " ", slug)
    return _match_city_in_text(slug.replace("-", " ").replace("_", " "))


def get_city_match_values(city: str) -> List[str]:
    """Return all city name variants that should match a filter for `city`."""
    canonical = normalize_city(city)
    if not canonical:
        return []

    if canonical in _CITY_MATCH_CACHE:
        return sorted(_CITY_MATCH_CACHE[canonical])

    variants: Set[str] = {canonical}
    for alias, mapped in CITY_ALIASES.items():
        if mapped == canonical:
            variants.add(alias.title())
            variants.add(mapped)

    _CITY_MATCH_CACHE[canonical] = variants
    return sorted(variants)


def resolve_record_city(
    scraped_location: str,
    search_city: str,
    explicit_city: str = "",
    hotel_name: str = "",
    url: str = "",
) -> Tuple[str, bool]:
    """Pick the best verified city for a hotel record.

    Never assigns the search query city unless a location signal confirms it.
    Returns (city, location_verified).

    Priority:
      1. Explicit city field on listing
      2. Parsed address / location text
      3. Hotel name (e.g. "Earl's Regency Kandy")
      4. URL slug
    """
    if explicit_city:
        city = parse_city_from_text(explicit_city)
        if city:
            return city, True

    if scraped_location:
        city = parse_city_from_text(scraped_location)
        if city:
            return city, True

    if hotel_name:
        city = parse_city_from_text(hotel_name)
        if city:
            return city, True

    if url:
        city = extract_city_from_url(url)
        if city:
            return city, True

    return "", False
