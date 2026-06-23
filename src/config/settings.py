"""Pydantic settings for hotel scraper configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
SELECTORS_FILE = SRC_DIR / "config" / "selectors.yaml"


class ScrapingSettings(BaseSettings):
    """Scraping-specific configuration."""

    request_timeout: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=2, ge=0, le=60)
    concurrent_requests: int = Field(default=5, ge=1, le=50)
    rate_limit_per_second: float = Field(default=0.5, gt=0, le=100)
    user_agent_rotation: bool = Field(default=True)
    proxy_rotation: bool = Field(default=False)


class ProxySettings(BaseSettings):
    """Proxy configuration for scraping."""

    proxy_list: List[str] = Field(default_factory=list)
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None

    @field_validator("proxy_list", mode="before")
    @classmethod
    def parse_proxy_list(cls, v):
        """Parse comma-separated proxy list from string."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v or []


class PlaywrightSettings(BaseSettings):
    """Playwright browser automation settings."""

    headless: bool = Field(default=True)
    browser: str = Field(default="chromium")
    slow_mo: int = Field(default=500, ge=0, le=10000)


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    database_url: str = Field(default="sqlite:///data/hotel_scraper.db")

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.database_url.lower()

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return "sqlite" in self.database_url.lower()


class SourceSettings(BaseSettings):
    """Source website base URLs."""

    booking_base_url: str = "https://www.booking.com"
    agoda_base_url: str = "https://www.agoda.com"
    expedia_base_url: str = "https://www.expedia.com"
    sltda_base_url: str = "https://www.sltda.gov.lk"
    datagovlk_base_url: str = "https://www.data.gov.lk"


class ScheduleSettings(BaseSettings):
    """Scheduler configuration."""

    schedule_interval_hours: int = Field(default=24, ge=1, le=168)
    schedule_time: str = Field(default="02:00")


class MonitoringSettings(BaseSettings):
    """Monitoring and metrics configuration."""

    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    enable_prometheus: bool = Field(default=False)


class APISettings(BaseSettings):
    """FastAPI server configuration."""

    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    api_workers: int = Field(default=1, ge=1, le=16)
    frontend_origin: str = "http://localhost:5173"


class Settings(BaseSettings):
    """Main application settings with Pydantic v2."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    env: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # --- Sub-configs ---
    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    playwright: PlaywrightSettings = Field(default_factory=PlaywrightSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    sources: SourceSettings = Field(default_factory=SourceSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    api: APISettings = Field(default_factory=APISettings)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v}")
        return v_upper

    def get_source_url(self, source: str) -> str:
        """Get the base URL for a given source."""
        mapping = {
            "booking": self.sources.booking_base_url,
            "agoda": self.sources.agoda_base_url,
            "expedia": self.sources.expedia_base_url,
            "sltda": self.sources.sltda_base_url,
            "datagovlk": self.sources.datagovlk_base_url,
        }
        return mapping.get(source.lower(), "")


# --- Selectors Loader ---

class Selectors:
    """CSS/XPath selectors loaded from YAML file."""

    def __init__(self, filepath: Path = SELECTORS_FILE):
        self._data = self._load(filepath)

    def _load(self, filepath: Path) -> dict:
        """Load selectors from YAML file."""
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get(self, source: str, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a selector for a specific source and key."""
        return self._data.get(source.lower(), {}).get(key, default)

    def get_all(self, source: str) -> dict:
        """Get all selectors for a specific source."""
        return self._data.get(source.lower(), {})

    def reload(self, filepath: Path = SELECTORS_FILE) -> None:
        """Reload selectors from file (useful for hot-updates)."""
        self._data = self._load(filepath)


# --- Singleton Pattern ---

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


@lru_cache()
def get_selectors() -> Selectors:
    """Get cached selectors instance."""
    return Selectors()
