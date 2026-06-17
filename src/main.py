#!/usr/bin/env python3
"""Main CLI entry point for the hotel scraper."""

import sys
import time
from datetime import date, datetime, timedelta
from typing import Optional

import click

from src.config.settings import get_settings
from src.monitoring.logger import configure_logging, get_logger
from src.monitoring.metrics import get_metrics
from src.scrapers import (
    AgodaScraper,
    BookingScraper,
    DataGovLkScraper,
    ExpediaScraper,
    SLTDAScraper,
)
from src.storage import CSVStorage, DatabaseStorage, JSONStorage, init_db
from src.utils.proxies import ProxyRotator

logger = get_logger(__name__)

# --- CLI Group ---

@click.group()
@click.option(
    "--env",
    type=click.Choice(["development", "production", "testing"]),
    default="development",
    help="Environment to run in",
)
@click.option("--debug/--no-debug", default=False, help="Enable debug mode")
@click.option(
    "--storage",
    type=click.Choice(["csv", "json", "database", "db"]),
    default="csv",
    help="Storage backend",
)
@click.option(
    "--database-url",
    envvar="DATABASE_URL",
    help="Database URL (for database storage)",
)
@click.pass_context
def cli(ctx, env, debug, storage, database_url):
    """Hotel Check-in Data Scraper CLI.

    Scrape hotel data from Booking.com, Agoda, Expedia, SLTDA, and data.gov.lk
    to analyze which hotels have the most check-ins each month.
    """
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj["env"] = env
    ctx.obj["debug"] = debug
    ctx.obj["storage_type"] = storage
    ctx.obj["database_url"] = database_url

    # Configure logging
    log_level = "DEBUG" if debug else "INFO"
    configure_logging(log_level=log_level)

    logger.info(f"Hotel Scraper starting | env={env} | storage={storage}")


def get_storage(ctx):
    """Get storage backend from context."""
    storage_type = ctx.obj.get("storage_type", "csv")

    if storage_type in ("database", "db"):
        db_url = ctx.obj.get("database_url")
        return DatabaseStorage(db_url)
    elif storage_type == "json":
        return JSONStorage()
    else:
        return CSVStorage()


def get_proxy_rotator():
    """Get proxy rotator if configured."""
    settings = get_settings()
    if settings.proxy.proxy_list:
        return ProxyRotator(
            proxy_list=settings.proxy.proxy_list,
            username=settings.proxy.proxy_username,
            password=settings.proxy.proxy_password,
        )
    return None


# --- Scrape Command ---

@cli.command()
@click.option(
    "--source",
    type=click.Choice(
        ["booking", "agoda", "expedia", "sltda", "datagovlk", "all"]
    ),
    required=True,
    help="Source to scrape",
)
@click.option("--city", default="Colombo", help="City to search")
@click.option(
    "--checkin",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
    help="Check-in date (YYYY-MM-DD)",
)
@click.option(
    "--checkout",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d"),
    help="Check-out date (YYYY-MM-DD)",
)
@click.option(
    "--max-pages", default=3, help="Maximum pages to scrape per source"
)
@click.option(
    "--use-playwright/--no-playwright",
    default=None,
    help="Use browser automation",
)
@click.option(
    "--year", type=int, default=None, help="Year for monthly analysis"
)
@click.option(
    "--month", type=int, default=None, help="Month for analysis (1-12)"
)
@click.pass_context
def scrape(
    ctx,
    source,
    city,
    checkin,
    checkout,
    max_pages,
    use_playwright,
    year,
    month,
):
    """Run scraper for a specific source."""
    storage = get_storage(ctx)
    proxy = get_proxy_rotator()
    metrics = get_metrics()
    start_time = time.time()

    sources_to_scrape = []
    if source == "all":
        sources_to_scrape = ["booking", "agoda", "expedia", "sltda", "datagovlk"]
    else:
        sources_to_scrape = [source]

    total_results = 0

    for src in sources_to_scrape:
        logger.info(f"=== Scraping {src} ===")
        try:
            results = _scrape_source(
                src,
                storage,
                proxy,
                city,
                checkin.date() if checkin else None,
                checkout.date() if checkout else None,
                max_pages,
                use_playwright,
                year,
                month,
            )
            total_results += len(results)
        except Exception as e:
            logger.error(f"Failed to scrape {src}: {e}")
            if ctx.obj.get("debug"):
                import traceback
                traceback.print_exc()
            continue

    duration = time.time() - start_time
    logger.info(
        f"=== Scrape Complete ===\n"
        f"Total sources: {len(sources_to_scrape)}\n"
        f"Total records: {total_results}\n"
        f"Duration: {duration:.1f}s"
    )


def _scrape_source(
    source: str,
    storage,
    proxy,
    city: str,
    checkin: Optional[date],
    checkout: Optional[date],
    max_pages: int,
    use_playwright: Optional[bool],
    year: Optional[int],
    month: Optional[int],
) -> list:
    """Scrape a single source."""

    if source == "booking":
        scraper = BookingScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else False

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "agoda":
        scraper = AgodaScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else True

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "expedia":
        scraper = ExpediaScraper(storage=storage, proxy_rotator=proxy)
        pw = use_playwright if use_playwright is not None else True

        if year and month:
            return scraper.scrape_with_monthly_dates(
                city=city, year=year, month=month, max_pages=max_pages
            )
        elif checkin and checkout:
            return scraper.scrape(
                city=city,
                checkin_date=checkin,
                checkout_date=checkout,
                max_pages=max_pages,
                use_playwright=pw,
            )

    elif source == "sltda":
        scraper = SLTDAScraper(storage=storage, proxy_rotator=proxy)
        return scraper.scrape(year=year, month=month)

    elif source == "datagovlk":
        scraper = DataGovLkScraper(storage=storage, proxy_rotator=proxy)
        return scraper.scrape()

    return []


# --- Analytics Commands ---

@cli.command()
@click.option("--city", default=None, help="Filter by city")
@click.option("--month", type=int, default=None, help="Filter by month")
@click.option("--year", type=int, default=None, help="Filter by year")
@click.option("--limit", default=20, help="Number of results")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
@click.pass_context
def top_hotels(ctx, city, month, year, limit, output_format):
    """Show top hotels by check-in count."""
    storage = get_storage(ctx)

    try:
        results = storage.get_top_hotels(
            city=city, month=month, year=year, limit=limit
        )

        if not results:
            click.echo("No data found. Run scraping first.")
            return

        if output_format == "json":
            import json
            click.echo(json.dumps(results, indent=2, default=str))
        elif output_format == "csv":
            import csv
            import sys
            if results:
                writer = csv.DictWriter(
                    sys.stdout, fieldnames=results[0].keys()
                )
                writer.writeheader()
                writer.writerows(results)
        else:
            click.echo(f"\\n{'Rank':<6} {'Hotel':<40} {'Check-ins':<12} {'Avg Rate':<12} {'Score':<8}")
            click.echo("-" * 80)
            for i, hotel in enumerate(results, 1):
                name = hotel.get("hotel_name", "Unknown")[:38]
                count = hotel.get("checkin_count", 0)
                rate = hotel.get("avg_nightly_rate", 0)
                score = hotel.get("avg_guest_score", 0)
                click.echo(
                    f"{i:<6} {name:<40} {count:<12} ${rate:<11.2f} {score:<8.1f}"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option("--city", default=None, help="Filter by city")
@click.option("--year", type=int, default=None, help="Filter by year")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.pass_context
def monthly(ctx, city, year, output_format):
    """Show monthly check-in statistics."""
    storage = get_storage(ctx)

    try:
        stats = storage.get_monthly_checkins(city=city, year=year)

        if output_format == "json":
            import json
            click.echo(json.dumps(stats, indent=2, default=str))
        else:
            click.echo(f"\\n{'Month':<12} {'Check-ins':<12} {'Hotels':<10}")
            click.echo("-" * 35)
            for month, count in sorted(stats.get("monthly_totals", {}).items()):
                hotels = stats.get("unique_hotels_per_month", {}).get(month, 0)
                click.echo(f"{month:<12} {count:<12} {hotels:<10}")

            click.echo(f"\\nTotal check-ins: {stats.get('total_checkins', 0)}")
            click.echo(f"Unique hotels: {stats.get('total_unique_hotels', 0)}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# --- Schedule Command ---

@cli.command()
@click.option(
    "--interval",
    type=int,
    default=24,
    help="Run interval in hours",
)
@click.option(
    "--sources",
    default="booking,agoda,sltda",
    help="Comma-separated list of sources",
)
@click.option(
    "--cities",
    default="Colombo,Kandy,Galle",
    help="Comma-separated list of cities",
)
@click.pass_context
def schedule(ctx, interval, sources, cities):
    """Run scraper on a schedule (daemon mode)."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    configure_logging()
    logger.info("Starting scheduler")

    scheduler = BlockingScheduler()
    source_list = [s.strip() for s in sources.split(",")]
    city_list = [c.strip() for c in cities.split(",")]

    def scheduled_job():
        """Job to run on schedule."""
        logger.info("Running scheduled scrape")
        for source in source_list:
            for city in city_list:
                try:
                    ctx.invoke(
                        scrape,
                        source=source,
                        city=city,
                        max_pages=2,
                    )
                except Exception as e:
                    logger.error(f"Scheduled scrape failed: {e}")

    # Add job
    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(hours=interval),
        id="scraper_job",
        name="Hotel Scraper",
        replace_existing=True,
    )

    # Run immediately first
    scheduled_job()

    logger.info(f"Scheduler running every {interval} hours")
    click.echo(f"Scheduler running. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
        scheduler.shutdown()


# --- Utility Commands ---

@cli.command()
@click.pass_context
def init_db(ctx):
    """Initialize database tables."""
    try:
        storage = DatabaseStorage(ctx.obj.get("database_url"))
        click.echo("Database initialized successfully")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def version():
    """Show version information."""
    click.echo("Hotel Scraper v1.0.0")
    click.echo("Python 3.10+")
    click.echo("Sources: Booking.com, Agoda, Expedia, SLTDA, data.gov.lk")


# --- Main Entry Point ---

if __name__ == "__main__":
    cli()
