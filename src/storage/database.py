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

        session = self.get_session()
        saved = 0

        try:
            for record in records:
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
    ) -> List[Dict[str, Any]]:
        """Load records with filtering."""
        session = self.get_session()
        try:
            query = session.query(HotelCheckinRecord)

            if source:
                query = query.filter(
                    HotelCheckinRecord.source == source.lower()
                )
            if city:
                query = query.filter(
                    func.lower(HotelCheckinRecord.city) == city.lower()
                )
            if checkin_date:
                query = query.filter(
                    HotelCheckinRecord.checkin_date == checkin_date
                )

            query = query.order_by(HotelCheckinRecord.scraped_at.desc())

            if limit:
                query = query.limit(limit)

            records = query.all()
            return [r.to_dict() for r in records]

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

            if city:
                query = query.filter(
                    func.lower(HotelCheckinRecord.city) == city.lower()
                )
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

            if city:
                month_query = month_query.filter(
                    func.lower(HotelCheckinRecord.city) == city.lower()
                )
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

        # Store extra fields as JSON
        known_fields = {
            "hotel_name", "source", "city", "country", "checkin_date",
            "checkout_date", "nightly_rate", "currency", "available_rooms",
            "occupancy_pct", "room_type", "guest_score", "review_count",
            "scraped_at", "url",
        }
        raw_data = {k: v for k, v in data.items() if k not in known_fields}

        return HotelCheckinRecord(
            hotel_name=data.get("hotel_name", "Unknown"),
            source=data.get("source", "unknown"),
            city=data.get("city", ""),
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
