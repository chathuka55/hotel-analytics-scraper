"""Per-OTA city / region identifiers for Sri Lankan destinations."""

from typing import Dict, Optional

# Agoda cityId values
AGODA_CITY_IDS: Dict[str, str] = {
    "colombo": "14932",
    "kandy": "4919",
    "galle": "21674",
    "negombo": "13409",
    "nuwara eliya": "21676",
    "bentota": "14781",
    "sigiriya": "16056",
    "ella": "13418",
    "mirissa": "21354",
    "trincomalee": "14782",
    "jaffna": "13424",
    "anuradhapura": "16058",
    "dambulla": "13413",
    "hikkaduwa": "16060",
    "unawatuna": "14783",
    "matara": "13425",
    "polonnaruwa": "16057",
    "kalutara": "13420",
    "beruwala": "14780",
    "arugam bay": "13410",
    "tangalle": "14784",
    "weligama": "21355",
    "ratnapura": "13426",
    "badulla": "13411",
    "batticaloa": "13412",
}

# Expedia / Hotels.com regionId values (Expedia Group)
EXPEDIA_REGION_IDS: Dict[str, str] = {
    "colombo": "6056893",
    "kandy": "6057007",
    "galle": "6057123",
    "negombo": "6056894",
    "nuwara eliya": "6057124",
    "bentota": "6057125",
    "sigiriya": "6057008",
    "ella": "6057126",
    "mirissa": "6057127",
    "trincomalee": "6057128",
    "jaffna": "6057129",
    "anuradhapura": "6057009",
    "dambulla": "6057010",
    "hikkaduwa": "6057130",
    "unawatuna": "6057131",
    "matara": "6057132",
    "polonnaruwa": "6057133",
    "kalutara": "6057134",
    "beruwala": "6057135",
    "tangalle": "6057136",
    "weligama": "6057137",
    "ratnapura": "6057138",
    "badulla": "6057139",
    "batticaloa": "6057140",
}

# Trip.com cityId (countryId=110 Sri Lanka)
TRIPCOM_CITY_IDS: Dict[str, str] = {
    "colombo": "357",
    "kandy": "358",
    "galle": "359",
    "negombo": "360",
    "nuwara eliya": "361",
    "bentota": "362",
    "sigiriya": "363",
    "ella": "364",
    "mirissa": "365",
    "trincomalee": "366",
    "jaffna": "367",
    "anuradhapura": "368",
    "dambulla": "369",
    "hikkaduwa": "370",
    "unawatuna": "371",
}

# TripAdvisor geoId (g-prefix in URLs)
TRIPADVISOR_GEO_IDS: Dict[str, str] = {
    "colombo": "293962",
    "kandy": "674794",
    "galle": "674786",
    "negombo": "674792",
    "nuwara eliya": "674798",
    "bentota": "674779",
    "sigiriya": "674800",
    "ella": "674783",
    "mirissa": "674791",
    "trincomalee": "674802",
    "jaffna": "674788",
    "anuradhapura": "674778",
    "dambulla": "674781",
    "hikkaduwa": "674787",
    "unawatuna": "674803",
    "matara": "674790",
    "polonnaruwa": "674796",
    "kalutara": "674789",
    "beruwala": "674780",
    "tangalle": "674801",
    "weligama": "674804",
    "ratnapura": "674797",
    "badulla": "674777",
    "batticaloa": "674776",
    "arugam bay": "674775",
}


def lookup_city_id(mapping: Dict[str, str], city_name: str) -> Optional[str]:
    """Look up an OTA city/region id from a city name."""
    if not city_name:
        return None
    return mapping.get(city_name.lower().strip())
