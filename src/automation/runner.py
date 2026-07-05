"""Run all configured scrapers on a schedule with logging and cache fallback."""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config.sources_registry import ALL_SOURCES, is_government_source
from src.monitoring.logger import get_logger
from src.scrapers.runner import run_source_scrape
from src.storage.database import DatabaseStorage
from src.storage.scrape_cache import (
    append_run_summary,
    load_cache,
    save_cache,
    update_source_cache,
)

logger = get_logger(__name__)

DEFAULT_CITIES = ["Colombo", "Kandy", "Galle"]


def _default_dates() -> tuple:
    checkin = datetime.utcnow().date() + timedelta(days=30)
    checkout = checkin + timedelta(days=2)
    return checkin, checkout


def run_automated_scrape(
    storage: Optional[DatabaseStorage] = None,
    cities: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    max_pages: int = 2,
    use_playwright: Optional[bool] = None,
    own_storage: bool = True,
) -> Dict[str, Any]:
    """Scrape every configured source, log outcomes, and persist cache.

    Failed sources do not remove existing DB rows — the UI continues to show
    the most recent successfully scraped data for that source.
    """
    city_list = cities or DEFAULT_CITIES
    source_list = sources or list(ALL_SOURCES)
    checkin, checkout = _default_dates()

    db = storage or DatabaseStorage()
    close_storage = own_storage and storage is None
    cache = load_cache()
    run_started = datetime.utcnow()
    run_results: List[Dict[str, Any]] = []
    total_records = 0

    logger.info(
        "Starting automated scrape | sources=%s | cities=%s",
        ",".join(source_list),
        ",".join(city_list),
    )

    try:
        for source in source_list:
            if is_government_source(source):
                targets = [("", source)]
            else:
                targets = [(city, source) for city in city_list]

            source_records = 0
            source_errors: List[str] = []

            for city, src in targets:
                log_id = db.log_scrape_start(src, city)
                started = time.time()
                try:
                    results = run_source_scrape(
                        src,
                        db,
                        None,
                        city,
                        checkin,
                        checkout,
                        max_pages,
                        use_playwright,
                        None,
                        None,
                    )
                    count = len(results)
                    source_records += count
                    total_records += count
                    duration = time.time() - started
                    db.log_scrape_complete(
                        log_id,
                        status="success",
                        records=count,
                        duration=duration,
                    )
                    data_at = db.get_source_latest_scraped_at(src)
                    update_source_cache(
                        cache,
                        src,
                        status="success",
                        records_scraped=count,
                        city=city,
                        duration_seconds=duration,
                        data_last_scraped_at=data_at,
                    )
                    run_results.append(
                        {
                            "source": src,
                            "city": city,
                            "status": "success",
                            "records_scraped": count,
                            "duration_seconds": round(duration, 2),
                        }
                    )
                    logger.info(
                        "Automated scrape OK | source=%s city=%s records=%d",
                        src,
                        city or "-",
                        count,
                    )
                except Exception as exc:
                    duration = time.time() - started
                    message = str(exc)
                    source_errors.append(message)
                    db.log_scrape_complete(
                        log_id,
                        status="failed",
                        error=message,
                        duration=duration,
                    )
                    data_at = db.get_source_latest_scraped_at(src)
                    update_source_cache(
                        cache,
                        src,
                        status="failed",
                        error=message,
                        city=city,
                        duration_seconds=duration,
                        data_last_scraped_at=data_at,
                    )
                    run_results.append(
                        {
                            "source": src,
                            "city": city,
                            "status": "failed",
                            "records_scraped": 0,
                            "error": message,
                            "duration_seconds": round(duration, 2),
                        }
                    )
                    logger.error(
                        "Automated scrape failed | source=%s city=%s error=%s",
                        src,
                        city or "-",
                        message,
                    )

            if source_errors and source_records == 0:
                logger.warning(
                    "Source %s unavailable — showing cached DB data if present",
                    source,
                )

        summary = {
            "started_at": run_started.replace(microsecond=0).isoformat(),
            "completed_at": datetime.utcnow().replace(microsecond=0).isoformat(),
            "sources_attempted": len(source_list),
            "jobs_run": len(run_results),
            "records_scraped": total_records,
            "results": run_results,
        }
        append_run_summary(cache, summary)
        cache_path = save_cache(cache)

        return {
            "records_scraped": total_records,
            "jobs_run": len(run_results),
            "sources": source_list,
            "results": run_results,
            "cache_path": str(cache_path),
        }
    finally:
        if close_storage:
            db.close()
