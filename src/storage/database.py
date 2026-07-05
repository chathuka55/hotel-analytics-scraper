"""Database storage using SQLAlchemy with SQLite and PostgreSQL support."""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.storage.base import BaseStorage
from src.utils.location import get_city_match_values, normalize_city
from src.utils.validators import filter_scraped_records, is_junk_record, JUNK_HOTEL_NAMES

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class HotelCheckinRecord(Base):
    """Database model for hotel check-in records."""

    __tablename__ = "hotel_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_name = Column(String(500), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    city = Column(String(200), nullable=False, index=True)
    country = Column(String(200), default="Sri Lanka")
    checkin_date = Column(Date, nullable=False, index=True)
    checkout_date = Column(Date, nullable=False)
    nightly_rate = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    available_rooms = Column(Integer, default=0)
    occupancy_pct = Column(Float, default=0.0)
    room_type = Column(String(200), default="")
    guest_score = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    url = Column(String(2000), default="")

    # Extra data as JSON for flexibility
    raw_data = Column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        address = ""
        if self.raw_data and isinstance(self.raw_data, dict):
            address = self.raw_data.get("address", "") or ""

        return {
            "id": self.id,
            "hotel_name": self.hotel_name,
            "source": self.source,
            "city": self.city,
            "country": self.country,
            "checkin_date": self.checkin_date.isoformat() if self.checkin_date else None,
            "checkout_date": self.checkout_date.isoformat() if self.checkout_date else None,
            "nightly_rate": self.nightly_rate,
            "currency": self.currency,
            "available_rooms": self.available_rooms,
            "occupancy_pct": self.occupancy_pct,
            "room_type": self.room_type,
            "guest_score": self.guest_score,
            "review_count": self.review_count,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "url": self.url,
            "address": address,
            "raw_data": self.raw_data,
        }


class ScrapeLog(Base):
    """Log of scraping runs."""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    city = Column(String(200), default="")
    status = Column(String(50), default="started")  # started, success, failed
    records_scraped = Column(Integer, default=0)
    error_message = Column(String(2000), default="")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)


class DatabaseStorage(BaseStorage):
    """Database storage using SQLAlchemy.

    Supports both SQLite (beginner) and PostgreSQL (production).
    Provides efficient querying, filtering, and aggregation.
    """

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database storage.

        Args:
            database_url: SQLAlchemy database URL
        """
        settings = get_settings()
        self.database_url = database_url or settings.database.database_url

        # Ensure directory exists for SQLite
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database storage initialized: {self.database_url}")

    @staticmethod
    def _record_to_dict(record: HotelCheckinRecord) -> Dict[str, Any]:
        """Merge ORM row with raw_data for junk checks."""
        data = record.to_dict()
        if record.raw_data and isinstance(record.raw_data, dict):
            data.update(record.raw_data)
        return data

    @staticmethod
    def _quality_filter(query):
        """Exclude unknown/incomplete rows from hotel analytics queries."""
        junk_names = [n for n in JUNK_HOTEL_NAMES if n]
        query = query.filter(
            ~func.lower(HotelCheckinRecord.hotel_name).in_(junk_names),
            HotelCheckinRecord.city != "",
            ~func.lower(HotelCheckinRecord.city).in_(junk_names),
            HotelCheckinRecord.source != "unknown",
            HotelCheckinRecord.source != "datagovlk",
        )
        return query

    def _apply_hotel_filters(self, query, city: Optional[str] = None):
        """Apply quality + city filters to a HotelCheckinRecord query."""
        query = self._quality_filter(query)
        return self._apply_city_filter(query, city)

    def _apply_city_filter(self, query, city: Optional[str]):
        """Filter by city including known aliases (e.g. Colombo City)."""
        if not city:
            return query
        variants = [v.lower() for v in get_city_match_values(city)]
        if not variants:
            return query.filter(
                func.lower(HotelCheckinRecord.city) == city.lower()
            )
        return query.filter(
            func.lower(HotelCheckinRecord.city).in_(variants)
        )

    def purge_unknown_records(self) -> int:
        """Delete junk/unknown records already stored in the database."""
        session = self.get_session()
        try:
            records = session.query(HotelCheckinRecord).all()
            count = 0
            for record in records:
                if is_junk_record(self._record_to_dict(record)):
                    session.delete(record)
                    count += 1
            session.commit()
            logger.info(f"Purged {count} unknown/junk records")
            return count
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def save(self, records: List[Dict[str, Any]]) -> int:
        """Save records to database.

        Args:
            records: List of hotel data dictionaries

        Returns:
            Number of records saved
        """
        if not records:
            return 0

        records = filter_scraped_records(records)
        if not records:
            return 0

        session = self.get_session()
        saved = 0

        try:
            for record in records:
                if is_junk_record(record):
                    continue
                try:
                    db_record = self._dict_to_record(record)
                    session.add(db_record)
                    saved += 1
                except Exception as e:
                    logger.warning(f"Failed to convert record: {e}")
                    continue

            session.commit()
            logger.info(f"Saved {saved} records to database")

        except Exception as e:
            session.rollback()
            logger.error(f"Database save failed: {e}")
            raise
        finally:
            session.close()

        return saved

    def load(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        checkin_date: Optional[date] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load records with filtering."""
        session = self.get_session()
        try:
            query = self._quality_filter(session.query(HotelCheckinRecord))

            if source:
                query = query.filter(
                    HotelCheckinRecord.source == source.lower()
                )
            query = self._apply_city_filter(query, city)
            if checkin_date:
                query = query.filter(
                    HotelCheckinRecord.checkin_date == checkin_date
                )

            query = query.order_by(HotelCheckinRecord.scraped_at.desc())

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            records = query.all()
            return [r.to_dict() for r in records]

        finally:
            session.close()

    def count(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
    ) -> int:
        """Count records matching the given filters.

        Args:
            source: Filter by source
            city: Filter by city

        Returns:
            Number of matching records
        """
        session = self.get_session()
        try:
            query = self._quality_filter(
                session.query(func.count(HotelCheckinRecord.id))
            )

            if source:
                query = query.filter(
                    HotelCheckinRecord.source == source.lower()
                )
            query = self._apply_city_filter(query, city)

            return query.scalar() or 0

        finally:
            session.close()

    def get_top_hotels(
        self,
        city: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top hotels by check-in count using SQL aggregation."""
        session = self.get_session()
        try:
            query = session.query(
                HotelCheckinRecord.hotel_name,
                HotelCheckinRecord.city,
                func.count(HotelCheckinRecord.id).label("checkin_count"),
                func.avg(HotelCheckinRecord.nightly_rate).label("avg_rate"),
                func.avg(HotelCheckinRecord.guest_score).label("avg_score"),
            )
            query = self._apply_hotel_filters(query, city)
            if month:
                query = query.filter(
                    func.extract("month", HotelCheckinRecord.checkin_date)
                    == month
                )
            if year:
                query = query.filter(
                    func.extract("year", HotelCheckinRecord.checkin_date)
                    == year
                )

            results = (
                query.group_by(
                    HotelCheckinRecord.hotel_name,
                    HotelCheckinRecord.city,
                )
                .order_by(func.count(HotelCheckinRecord.id).desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "hotel_name": r.hotel_name,
                    "city": r.city,
                    "checkin_count": r.checkin_count,
                    "avg_nightly_rate": round(r.avg_rate, 2) if r.avg_rate else 0,
                    "avg_guest_score": round(r.avg_score, 2) if r.avg_score else 0,
                }
                for r in results
            ]

        finally:
            session.close()

    def get_monthly_checkins(
        self,
        city: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly check-in statistics using SQL aggregation."""
        session = self.get_session()
        try:
            # Monthly totals
            month_query = session.query(
                func.extract("year", HotelCheckinRecord.checkin_date).label(
                    "year"
                ),
                func.extract("month", HotelCheckinRecord.checkin_date).label(
                    "month"
                ),
                func.count(HotelCheckinRecord.id).label("total"),
                func.count(
                    func.distinct(HotelCheckinRecord.hotel_name)
                ).label("unique_hotels"),
            )
            month_query = self._apply_hotel_filters(month_query, city)
            if year:
                month_query = month_query.filter(
                    func.extract("year", HotelCheckinRecord.checkin_date)
                    == year
                )

            month_results = (
                month_query.group_by(
                    func.extract("year", HotelCheckinRecord.checkin_date),
                    func.extract("month", HotelCheckinRecord.checkin_date),
                )
                .order_by(
                    func.extract("year", HotelCheckinRecord.checkin_date),
                    func.extract("month", HotelCheckinRecord.checkin_date),
                )
                .all()
            )

            monthly_totals = {}
            unique_hotels = {}
            for r in month_results:
                key = f"{int(r.year)}-{int(r.month):02d}"
                monthly_totals[key] = r.total
                unique_hotels[key] = r.unique_hotels

            # Overall stats
            total_query = session.query(
                func.count(HotelCheckinRecord.id).label("total"),
                func.count(
                    func.distinct(HotelCheckinRecord.hotel_name)
                ).label("hotels"),
                func.count(
                    func.distinct(HotelCheckinRecord.city)
                ).label("cities"),
            )

            if city:
                total_query = total_query.filter(
                    func.lower(HotelCheckinRecord.city) == city.lower()
                )
            if year:
                total_query = total_query.filter(
                    func.extract("year", HotelCheckinRecord.checkin_date)
                    == year
                )

            total_result = total_query.first()

            return {
                "monthly_totals": monthly_totals,
                "unique_hotels_per_month": unique_hotels,
                "total_checkins": total_result.total if total_result else 0,
                "total_unique_hotels": total_result.hotels if total_result else 0,
                "total_cities": total_result.cities if total_result else 0,
            }

        finally:
            session.close()

    def get_overview(self, city: Optional[str] = None) -> Dict[str, Any]:
        """Headline KPIs for the dashboard hero section.

        Returns aggregate counts plus the single best hotel for each of the
        three questions the dashboard answers: most check-ins, lowest price
        (with a decent rating), and best rated overall.
        """
        session = self.get_session()
        try:
            def _scoped(query):
                return self._apply_hotel_filters(query, city)

            totals = _scoped(
                session.query(
                    func.count(HotelCheckinRecord.id).label("records"),
                    func.count(
                        func.distinct(HotelCheckinRecord.hotel_name)
                    ).label("hotels"),
                    func.count(
                        func.distinct(HotelCheckinRecord.city)
                    ).label("cities"),
                    func.avg(HotelCheckinRecord.nightly_rate).label("avg_rate"),
                    func.min(HotelCheckinRecord.nightly_rate).label("min_rate"),
                    func.max(HotelCheckinRecord.nightly_rate).label("max_rate"),
                    func.avg(HotelCheckinRecord.guest_score).label("avg_score"),
                )
            ).first()

            # Per-source record counts
            source_rows = _scoped(
                session.query(
                    HotelCheckinRecord.source,
                    func.count(HotelCheckinRecord.id).label("count"),
                )
            ).group_by(HotelCheckinRecord.source).all()

            most_checkins = self.get_top_hotels(city=city, limit=1)
            cheapest = self.get_cheapest(city=city, min_score=8.0, limit=1)
            best_rated = self.get_best_rated(city=city, min_reviews=50, limit=1)
            best_value = self.get_best_value(city=city, limit=1)

            return {
                "total_records": totals.records if totals else 0,
                "total_hotels": totals.hotels if totals else 0,
                "total_cities": totals.cities if totals else 0,
                "avg_nightly_rate": round(totals.avg_rate, 2)
                if totals and totals.avg_rate
                else 0,
                "min_nightly_rate": round(totals.min_rate, 2)
                if totals and totals.min_rate
                else 0,
                "max_nightly_rate": round(totals.max_rate, 2)
                if totals and totals.max_rate
                else 0,
                "avg_guest_score": round(totals.avg_score, 2)
                if totals and totals.avg_score
                else 0,
                "by_source": {r.source: r.count for r in source_rows},
                "most_checkins": most_checkins[0] if most_checkins else None,
                "cheapest": cheapest[0] if cheapest else None,
                "best_rated": best_rated[0] if best_rated else None,
                "best_value": best_value[0] if best_value else None,
            }
        finally:
            session.close()

    def get_cheapest(
        self,
        city: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Cheapest individual offers, optionally filtered by a minimum score.

        Useful for the "lowest price (good rating)" view: pass min_score to
        avoid surfacing rock-bottom prices attached to poorly rated hotels.
        """
        session = self.get_session()
        try:
            query = self._apply_hotel_filters(
                session.query(HotelCheckinRecord).filter(
                    HotelCheckinRecord.nightly_rate > 0
                ),
                city,
            )
            if min_score:
                query = query.filter(
                    HotelCheckinRecord.guest_score >= min_score
                )

            records = (
                query.order_by(HotelCheckinRecord.nightly_rate.asc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in records]
        finally:
            session.close()

    def get_best_rated(
        self,
        city: Optional[str] = None,
        min_reviews: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Hotels ranked by average guest score (with a review-count floor)."""
        session = self.get_session()
        try:
            query = session.query(
                HotelCheckinRecord.hotel_name,
                HotelCheckinRecord.city,
                func.avg(HotelCheckinRecord.guest_score).label("avg_score"),
                func.avg(HotelCheckinRecord.nightly_rate).label("avg_rate"),
                func.max(HotelCheckinRecord.review_count).label("review_count"),
                func.count(HotelCheckinRecord.id).label("checkin_count"),
            )
            query = self._apply_hotel_filters(query, city)

            query = query.group_by(
                HotelCheckinRecord.hotel_name, HotelCheckinRecord.city
            )
            if min_reviews:
                query = query.having(
                    func.max(HotelCheckinRecord.review_count) >= min_reviews
                )

            results = (
                query.order_by(
                    func.avg(HotelCheckinRecord.guest_score).desc()
                )
                .limit(limit)
                .all()
            )
            return [
                {
                    "hotel_name": r.hotel_name,
                    "city": r.city,
                    "avg_guest_score": round(r.avg_score, 2) if r.avg_score else 0,
                    "avg_nightly_rate": round(r.avg_rate, 2) if r.avg_rate else 0,
                    "review_count": r.review_count or 0,
                    "checkin_count": r.checkin_count,
                }
                for r in results
            ]
        finally:
            session.close()

    def get_best_value(
        self,
        city: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Best value = high guest score per dollar of nightly rate.

        Computes (avg_score / avg_rate) * 100 so a well-rated, affordable
        hotel ranks above an expensive one with the same score.
        """
        session = self.get_session()
        try:
            query = self._apply_hotel_filters(
                session.query(
                    HotelCheckinRecord.hotel_name,
                    HotelCheckinRecord.city,
                    func.avg(HotelCheckinRecord.guest_score).label("avg_score"),
                    func.avg(HotelCheckinRecord.nightly_rate).label("avg_rate"),
                    func.count(HotelCheckinRecord.id).label("checkin_count"),
                ).filter(HotelCheckinRecord.nightly_rate > 0),
                city,
            )

            results = (
                query.group_by(
                    HotelCheckinRecord.hotel_name, HotelCheckinRecord.city
                )
                .having(func.avg(HotelCheckinRecord.guest_score) >= 7.0)
                .all()
            )

            scored = []
            for r in results:
                if not r.avg_rate:
                    continue
                value_score = round((r.avg_score / r.avg_rate) * 100, 3)
                scored.append(
                    {
                        "hotel_name": r.hotel_name,
                        "city": r.city,
                        "avg_guest_score": round(r.avg_score, 2),
                        "avg_nightly_rate": round(r.avg_rate, 2),
                        "checkin_count": r.checkin_count,
                        "value_score": value_score,
                    }
                )

            scored.sort(key=lambda x: x["value_score"], reverse=True)
            return scored[:limit]
        finally:
            session.close()

    def get_source_latest_scraped_at(self, source: str) -> Optional[str]:
        """Latest scraped_at timestamp for a source's hotel records."""
        session = self.get_session()
        try:
            latest = (
                session.query(func.max(HotelCheckinRecord.scraped_at))
                .filter(HotelCheckinRecord.source == source.lower())
                .scalar()
            )
            return latest.isoformat() if latest else None
        finally:
            session.close()

    def get_source_record_count(self, source: str) -> int:
        """Count quality-filtered records for a source."""
        session = self.get_session()
        try:
            query = session.query(HotelCheckinRecord).filter(
                HotelCheckinRecord.source == source.lower()
            )
            query = self._apply_hotel_filters(query)
            return query.count()
        finally:
            session.close()

    def get_last_scraped_summary(self) -> Dict[str, Any]:
        """Per-source scrape status for the UI and automation cache."""
        from src.config.sources_registry import ALL_SOURCES, SOURCE_LABELS
        from src.storage.scrape_cache import load_cache

        cache = load_cache()
        cache_sources = cache.get("sources", {})
        session = self.get_session()
        sources_summary: List[Dict[str, Any]] = []

        try:
            for source_id in ALL_SOURCES:
                latest_log = (
                    session.query(ScrapeLog)
                    .filter(ScrapeLog.source == source_id)
                    .order_by(ScrapeLog.started_at.desc())
                    .first()
                )
                latest_success_log = (
                    session.query(ScrapeLog)
                    .filter(
                        ScrapeLog.source == source_id,
                        ScrapeLog.status == "success",
                    )
                    .order_by(ScrapeLog.completed_at.desc())
                    .first()
                )
                data_at = (
                    session.query(func.max(HotelCheckinRecord.scraped_at))
                    .filter(HotelCheckinRecord.source == source_id)
                    .scalar()
                )
                count_query = session.query(HotelCheckinRecord).filter(
                    HotelCheckinRecord.source == source_id
                )
                records_in_db = self._apply_hotel_filters(count_query).count()
                cached = cache_sources.get(source_id, {})

                last_attempt_at = None
                last_status = cached.get("last_status", "never")
                last_error = cached.get("last_error", "")
                if latest_log:
                    last_attempt_at = latest_log.started_at
                    last_status = latest_log.status
                    last_error = latest_log.error_message or ""

                log_success_dt = (
                    latest_success_log.completed_at if latest_success_log else None
                )
                candidates = [d for d in (data_at, log_success_dt) if d]
                last_scraped_at = max(candidates) if candidates else None

                using_cached_data = bool(
                    records_in_db > 0
                    and last_status == "failed"
                    and data_at is not None
                )

                sources_summary.append(
                    {
                        "source": source_id,
                        "label": SOURCE_LABELS.get(source_id, source_id.title()),
                        "last_scraped_at": last_scraped_at.isoformat() if last_scraped_at else None,
                        "last_attempt_at": last_attempt_at.isoformat() if last_attempt_at else cached.get("last_attempt_at"),
                        "last_status": last_status if latest_log else cached.get("last_status", "never"),
                        "last_error": last_error or cached.get("last_error", ""),
                        "records_in_db": records_in_db,
                        "using_cached_data": using_cached_data or cached.get("using_cached_data", False),
                    }
                )
        finally:
            session.close()

        scraped_times = [
            s["last_scraped_at"]
            for s in sources_summary
            if s.get("last_scraped_at")
        ]
        overall_last = max(scraped_times) if scraped_times else None

        return {
            "overall_last_scraped_at": overall_last,
            "last_automation_run_at": cache.get("last_automation_run_at"),
            "data_from_cache": any(s.get("using_cached_data") for s in sources_summary),
            "sources": sources_summary,
        }

    def log_scrape_start(
        self, source: str, city: str = ""
    ) -> int:
        """Log the start of a scraping run.

        Returns:
            Log entry ID
        """
        session = self.get_session()
        try:
            log = ScrapeLog(source=source, city=city, status="started")
            session.add(log)
            session.commit()
            return log.id
        finally:
            session.close()

    def log_scrape_complete(
        self,
        log_id: int,
        status: str,
        records: int = 0,
        error: str = "",
        duration: Optional[float] = None,
    ) -> None:
        """Log the completion of a scraping run."""
        session = self.get_session()
        try:
            log = session.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
            if log:
                log.status = status
                log.records_scraped = records
                log.error_message = error
                log.completed_at = datetime.utcnow()
                log.duration_seconds = duration
                session.commit()
        finally:
            session.close()

    def get_scrape_log(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Get a single scrape log entry by id.

        Args:
            log_id: Scrape log entry id

        Returns:
            Log entry dict, or None if not found
        """
        session = self.get_session()
        try:
            log = session.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
            if not log:
                return None

            return {
                "id": log.id,
                "source": log.source,
                "city": log.city,
                "status": log.status,
                "records_scraped": log.records_scraped,
                "error_message": log.error_message,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_seconds": log.duration_seconds,
            }
        finally:
            session.close()

    def get_scrape_history(
        self, source: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get history of scraping runs."""
        session = self.get_session()
        try:
            query = session.query(ScrapeLog)
            if source:
                query = query.filter(ScrapeLog.source == source)

            logs = (
                query.order_by(ScrapeLog.started_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": log.id,
                    "source": log.source,
                    "city": log.city,
                    "status": log.status,
                    "records_scraped": log.records_scraped,
                    "error_message": log.error_message,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_seconds": log.duration_seconds,
                }
                for log in logs
            ]
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()

    def _dict_to_record(
        self, data: Dict[str, Any]
    ) -> HotelCheckinRecord:
        """Convert dictionary to database record.

        Args:
            data: Hotel data dictionary

        Returns:
            HotelCheckinRecord instance
        """
        # Handle date fields
        checkin = data.get("checkin_date")
        if isinstance(checkin, str):
            checkin = datetime.fromisoformat(checkin).date()

        checkout = data.get("checkout_date")
        if isinstance(checkout, str):
            checkout = datetime.fromisoformat(checkout).date()

        scraped = data.get("scraped_at")
        if isinstance(scraped, str):
            scraped = datetime.fromisoformat(scraped)
        elif not scraped:
            scraped = datetime.utcnow()

        # Some sources (SLTDA / data.gov.lk report rows) carry no stay dates.
        # The check-in date column is NOT NULL, so fall back to the scrape
        # date rather than failing the whole batch insert.
        if checkin is None:
            checkin = scraped.date()
        if checkout is None:
            checkout = checkin

        # Store extra fields as JSON
        known_fields = {
            "hotel_name", "source", "city", "country", "checkin_date",
            "checkout_date", "nightly_rate", "currency", "available_rooms",
            "occupancy_pct", "room_type", "guest_score", "review_count",
            "scraped_at", "url", "address", "search_city", "location_verified",
        }
        raw_data = {k: v for k, v in data.items() if k not in known_fields}
        for extra_key in ("address", "search_city", "location_verified", "record_type"):
            if extra_key in data and data[extra_key] not in (None, ""):
                raw_data[extra_key] = data[extra_key]

        city_value = data.get("city", "")
        if city_value:
            city_value = normalize_city(city_value)

        hotel_name = (data.get("hotel_name") or "").strip()
        if not hotel_name:
            hotel_name = ""

        return HotelCheckinRecord(
            hotel_name=hotel_name,
            source=(data.get("source") or "").lower(),
            city=city_value,
            country=data.get("country", "Sri Lanka"),
            checkin_date=checkin,
            checkout_date=checkout,
            nightly_rate=float(data.get("nightly_rate", 0) or 0),
            currency=data.get("currency", "USD"),
            available_rooms=int(data.get("available_rooms", 0) or 0),
            occupancy_pct=float(data.get("occupancy_pct", 0) or 0),
            room_type=data.get("room_type", ""),
            guest_score=float(data.get("guest_score", 0) or 0),
            review_count=int(data.get("review_count", 0) or 0),
            scraped_at=scraped,
            url=data.get("url", ""),
            raw_data=raw_data if raw_data else None,
        )

    def __repr__(self) -> str:
        return f"DatabaseStorage({self.database_url})"


def init_db(database_url: Optional[str] = None) -> DatabaseStorage:
    """Initialize database and return storage instance.

    Args:
        database_url: Database connection URL

    Returns:
        DatabaseStorage instance
    """
    return DatabaseStorage(database_url)
