"""Vercel Python entrypoint for the FastAPI app.

Vercel routes /api/* to this module. The FastAPI routes already use the
/api prefix, so the browser URLs match production paths.
"""

from src.api.main import app

__all__ = ["app"]
