"""FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
(also wired up via `make api` and the docker-compose `api` service)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import hotels, meta, scrape, stats
from src.config.settings import get_settings
from src.monitoring.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title="Hotel Scraper API",
    description="Exposes scraped Sri Lanka hotel check-in data to the React frontend.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.api.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hotels.router)
app.include_router(stats.router)
app.include_router(scrape.router)
app.include_router(meta.router)


@app.on_event("startup")
def ensure_sample_data():
    """Load real Sri Lankan hotel data when the database is empty."""
    try:
        from src.data.sri_lanka_hotels import generate_real_hotel_records
        from src.storage.database import DatabaseStorage

        storage = DatabaseStorage()
        try:
            if storage.count() == 0:
                records = generate_real_hotel_records(250)
                saved = storage.save(records)
                logger.info(f"Auto-seeded {saved} real hotel records (DB was empty)")
        finally:
            storage.close()
    except Exception as e:
        logger.warning(f"Auto-seed skipped: {e}")


@app.get("/api/health")
def health():
    """Liveness check."""
    return {"status": "ok"}
