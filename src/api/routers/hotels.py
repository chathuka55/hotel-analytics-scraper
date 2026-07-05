"""Endpoints for the top-hotels leaderboard and raw hotel listing."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_storage
from src.api.schemas import HotelListResponse, HotelRecord, RatedHotel, TopHotel
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


@router.get("/cheapest", response_model=list[HotelRecord])
def get_cheapest_hotels(
    city: Optional[str] = None,
    min_score: float = Query(default=0.0, ge=0, le=10),
    limit: int = Query(default=10, ge=1, le=100),
    storage: DatabaseStorage = Depends(get_storage),
):
    """Cheapest offers, optionally filtered by a minimum guest score."""
    return storage.get_cheapest(city=city, min_score=min_score, limit=limit)


@router.get("/best-rated", response_model=list[RatedHotel])
def get_best_rated_hotels(
    city: Optional[str] = None,
    min_reviews: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    storage: DatabaseStorage = Depends(get_storage),
):
    """Hotels ranked by average guest score."""
    return storage.get_best_rated(city=city, min_reviews=min_reviews, limit=limit)


@router.get("/best-value", response_model=list[RatedHotel])
def get_best_value_hotels(
    city: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    storage: DatabaseStorage = Depends(get_storage),
):
    """Hotels ranked by rating-per-dollar value score."""
    return storage.get_best_value(city=city, limit=limit)


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
