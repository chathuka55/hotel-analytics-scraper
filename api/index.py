"""Vercel Python entrypoint for the FastAPI app + dashboard static files."""

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.main import app

STATIC_DIR = Path(__file__).resolve().parent / "static"


if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def spa_index():
        return FileResponse(STATIC_DIR / "index.html")


__all__ = ["app"]
