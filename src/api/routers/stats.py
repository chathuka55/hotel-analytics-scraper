"""Endpoints for monthly check-in statistics."""

from typing import Optional

from fastapi import APIRouter, Depends

from src.api.deps import get_storage
from src.api.schemas import MonthlyStats, Overview
from src.storage.database import DatabaseStorage

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/monthly", response_model=MonthlyStats)
def get_monthly_stats(
    city: Optional[str] = None,
    year: Optional[int] = None,
    storage: DatabaseStorage = Depends(get_storage),
):
    """Monthly check-in totals and unique-hotel counts."""
    return storage.get_monthly_checkins(city=city, year=year)


@router.get("/overview", response_model=Overview)
def get_overview(
    city: Optional[str] = None,
    storage: DatabaseStorage = Depends(get_storage),
):
    """Headline KPIs plus the best hotel for each key metric."""
    return storage.get_overview(city=city)
