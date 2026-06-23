"""Endpoints for the top-hotels leaderboard and raw hotel listing."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_storage
from src.api.schemas import HotelListResponse, TopHotel
from src.storage.database import DatabaseStorage

router = APIRouter(prefix="/api/hotels", tags=["hotels"])


@router.get("/top", response_model=list[TopHotel])
def get_top_hotels(
    city: Optional[str] = None,
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = None,
    limit: int = Query(default=10, ge=1, le=100),
    storage: DatabaseStorage = Depends(get_storage),
):
    """Top hotels ranked by check-in count."""
    return storage.get_top_hotels(city=city, month=month, year=year, limit=limit)


@router.get("", response_model=HotelListResponse)
def list_hotels(
    source: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    storage: DatabaseStorage = Depends(get_storage),
):
    """Paginated raw hotel record listing, filterable by source/city."""
    items = storage.load(source=source, city=city, limit=limit, offset=offset)
    total = storage.count(source=source, city=city)
    return {"items": items, "total": total}
