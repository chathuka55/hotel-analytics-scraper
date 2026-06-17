"""Structured logging with loguru for the hotel scraper."""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config.settings import get_settings

# Remove default handler
logger.remove()

# Log format
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Detailed format for file logging
DETAILED_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | {message} | "
    "{extra}"
)


def configure_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    serialize: bool = False,
) -> None:
    """Configure structured logging for the scraper.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        serialize: Whether to output JSON serialized logs
    """
    settings = get_settings()
    level = (log_level or settings.log_level).upper()

    # Console handler
    logger.add(
        sys.stderr,
        level=level,
        format=LOG_FORMAT,
        serialize=serialize,
        enqueue=True,
        colorize=True,
    )

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level=level,
            format=DETAILED_FORMAT,
            serialize=serialize,
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            enqueue=True,
        )
    else:
        # Default log file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        logger.add(
            str(log_dir / "scraper_{time:YYYY-MM-DD}.log"),
            level=level,
            format=DETAILED_FORMAT,
            serialize=serialize,
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            enqueue=True,
        )

    logger.info(f"Logging configured with level={level}")


@lru_cache()
def get_logger(name: str = "hotel_scraper"):
    """Get a logger instance with contextual binding.

    Args:
        name: Logger name for identification

    Returns:
        loguru.Logger: Configured logger instance
    """
    return logger.bind(service=name)
