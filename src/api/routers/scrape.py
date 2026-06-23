"""Endpoints to trigger a scrape job and poll its status."""

import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.deps import get_storage
from src.api.schemas import ScrapeJobAccepted, ScrapeJobStatus, ScrapeRequest
from src.monitoring.logger import get_logger
from src.scrapers.runner import run_source_scrape
from src.storage.database import DatabaseStorage

logger = get_logger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


def _run_job(
    log_id: int,
    source: str,
    city: str,
    checkin,
    checkout,
    max_pages: int,
) -> None:
    """Run the scrape and record the outcome in the ScrapeLog table.

    Runs in a background thread (FastAPI BackgroundTasks), so it gets its
    own DatabaseStorage/session rather than sharing the request-scoped one.
    """
    storage = DatabaseStorage()
    start = time.time()
    try:
        results = run_source_scrape(
            source,
            storage,
            None,
            city,
            checkin,
            checkout,
            max_pages,
            None,
            None,
            None,
        )
        storage.log_scrape_complete(
            log_id,
            status="success",
            records=len(results),
            duration=time.time() - start,
        )
    except Exception as e:
        logger.error(f"Background scrape job {log_id} failed: {e}")
        storage.log_scrape_complete(
            log_id,
            status="failed",
            error=str(e),
            duration=time.time() - start,
        )
    finally:
        storage.close()


@router.post("", response_model=ScrapeJobAccepted)
def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    storage: DatabaseStorage = Depends(get_storage),
):
    """Start a scrape job in the background and return its log id immediately."""
    valid_sources = {"booking", "agoda", "expedia", "sltda", "datagovlk"}
    if request.source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Unknown source: {request.source}")

    log_id = storage.log_scrape_start(request.source, request.city)

    background_tasks.add_task(
        _run_job,
        log_id,
        request.source,
        request.city,
        request.checkin_date,
        request.checkout_date,
        request.max_pages,
    )

    return {"log_id": log_id, "status": "started"}


@router.get("/history", response_model=list[ScrapeJobStatus])
def scrape_history(
    source: Optional[str] = None,
    limit: int = 50,
    storage: DatabaseStorage = Depends(get_storage),
):
    """Recent scrape job history."""
    return storage.get_scrape_history(source=source, limit=limit)


@router.get("/{log_id}", response_model=ScrapeJobStatus)
def scrape_status(
    log_id: int,
    storage: DatabaseStorage = Depends(get_storage),
):
    """Poll the status of a single scrape job."""
    log = storage.get_scrape_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Scrape job not found")
    return log
