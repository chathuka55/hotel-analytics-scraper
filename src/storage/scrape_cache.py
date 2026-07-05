"""File-backed cache for automation scrape runs and fallback status."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CACHE_DIR = Path("data/cache")
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "scrape_status.json"


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def load_cache(cache_file: Optional[Path] = None) -> Dict[str, Any]:
    """Load scrape status cache from disk."""
    path = cache_file or DEFAULT_CACHE_FILE
    if not path.exists():
        return {"updated_at": None, "last_automation_run_at": None, "sources": {}, "runs": []}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data.setdefault("sources", {})
            data.setdefault("runs", [])
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"Could not read scrape cache {path}: {exc}")

    return {"updated_at": None, "last_automation_run_at": None, "sources": {}, "runs": []}


def save_cache(data: Dict[str, Any], cache_file: Optional[Path] = None) -> Path:
    """Persist scrape status cache to disk."""
    path = cache_file or DEFAULT_CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _utc_now_iso()

    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, default=str)

    return path


def update_source_cache(
    cache: Dict[str, Any],
    source: str,
    *,
    status: str,
    records_scraped: int = 0,
    error: str = "",
    city: str = "",
    duration_seconds: Optional[float] = None,
    data_last_scraped_at: Optional[str] = None,
) -> None:
    """Merge one source result into the in-memory cache payload."""
    now = _utc_now_iso()
    entry = cache.setdefault("sources", {}).setdefault(source, {})
    entry["last_attempt_at"] = now
    entry["last_status"] = status
    entry["last_error"] = error or ""
    entry["last_city"] = city
    entry["records_scraped"] = records_scraped
    if duration_seconds is not None:
        entry["duration_seconds"] = round(duration_seconds, 2)

    if status == "success":
        entry["last_success_at"] = now
        entry["using_cached_data"] = False
        if data_last_scraped_at:
            entry["data_last_scraped_at"] = data_last_scraped_at
    elif entry.get("data_last_scraped_at"):
        entry["using_cached_data"] = True
    elif data_last_scraped_at:
        entry["data_last_scraped_at"] = data_last_scraped_at
        entry["using_cached_data"] = True


def append_run_summary(cache: Dict[str, Any], summary: Dict[str, Any], keep: int = 24) -> None:
    """Keep a rolling history of automation runs."""
    runs = cache.setdefault("runs", [])
    runs.insert(0, summary)
    cache["runs"] = runs[:keep]
    cache["last_automation_run_at"] = summary.get("completed_at") or _utc_now_iso()
