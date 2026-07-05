#!/usr/bin/env python3
"""Run the hourly automation scrape (all sources, all cities)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.automation.runner import run_automated_scrape
from src.monitoring.logger import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> int:
    configure_logging()
    summary = run_automated_scrape()
    logger.info("Automation complete: %s", json.dumps(summary, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
