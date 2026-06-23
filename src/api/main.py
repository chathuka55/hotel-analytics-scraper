"""FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
(also wired up via `make api` and the docker-compose `api` service)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import hotels, meta, scrape, stats
from src.config.settings import get_settings

settings = get_settings()

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


@app.get("/api/health")
def health():
    """Liveness check."""
    return {"status": "ok"}
