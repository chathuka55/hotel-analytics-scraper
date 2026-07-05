.PHONY: help install install-dev test test-cov lint format clean docker-build docker-run run scrape-booking scrape-agoda scrape-expedia scrape-sltda scrape-datagovlk run-all scrape-automation scrape-automation-hourly automation-setup db-init seed-db docs api scheduler stack

PYTHON := python
PIP := pip
VENV := venv

# Default SQLite DB used by automation, API, and GitHub Actions
DATABASE_URL ?= sqlite:///data/hotel_scraper.db
export DATABASE_URL

AUTOMATION_SOURCES := all
AUTOMATION_CITIES := Colombo,Kandy,Galle
AUTOMATION_INTERVAL_HOURS := 1

help:
	@echo "Hotel Scraper - Available Commands:"
	@echo ""
	@echo "  make install              Install production dependencies"
	@echo "  make install-dev          Install with dev dependencies"
	@echo "  make automation-setup     Install deps, Playwright, and init DB"
	@echo "  make scrape-automation    Run one automated pass (all sources + cache)"
	@echo "  make scrape-automation-hourly  Run automation every hour (daemon)"
	@echo "  make scheduler            Alias for scrape-automation-hourly"
	@echo "  make stack                Start API + hourly scraper via Docker Compose"
	@echo "  make test                 Run all tests"
	@echo "  make test-cov             Run tests with coverage"
	@echo "  make lint                 Run linters (ruff, mypy)"
	@echo "  make format               Format code (black, ruff)"
	@echo "  make clean                Remove cache and temp files"
	@echo "  make docker-build         Build Docker image"
	@echo "  make docker-run           Run Docker container"
	@echo "  make scrape-booking       Run Booking.com scraper"
	@echo "  make scrape-agoda         Run Agoda.com scraper"
	@echo "  make scrape-expedia       Run Expedia.com scraper"
	@echo "  make scrape-sltda         Run SLTDA scraper"
	@echo "  make run-all              Run all scrapers (legacy shell script)"
	@echo "  make db-init              Initialize database"
	@echo "  make seed-db              Seed database with sample data"
	@echo "  make api                  Run FastAPI server"

install:
	$(PIP) install -r requirements.txt
	playwright install chromium

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev,api]"
	playwright install chromium

automation-setup: install db-init
	@echo "Automation ready. DATABASE_URL=$(DATABASE_URL)"
	@echo "Run once:  make scrape-automation"
	@echo "Run hourly: make scrape-automation-hourly"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

test-live:
	pytest tests/ -v -m live

lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ .coverage/ htmlcov/ .mypy_cache/ .ruff_cache/

docker-build:
	docker build -t hotel-scraper:latest .

docker-run:
	docker run --rm --env-file .env -e DATABASE_URL=$(DATABASE_URL) hotel-scraper:latest

stack:
	docker compose up --build db scraper api

run:
	$(PYTHON) -m src.main

scrape-booking:
	$(PYTHON) -m src.main --storage database scrape --source booking --city Colombo

scrape-agoda:
	$(PYTHON) -m src.main --storage database scrape --source agoda --city Colombo

scrape-expedia:
	$(PYTHON) -m src.main --storage database scrape --source expedia --city Colombo

scrape-sltda:
	$(PYTHON) -m src.main --storage database scrape --source sltda

scrape-datagovlk:
	$(PYTHON) -m src.main --storage database scrape --source datagovlk

run-all:
	bash scripts/run_all.sh

scrape-automation: db-init
	$(PYTHON) scripts/automated_scrape.py

scrape-automation-hourly: db-init
	$(PYTHON) -m src.main --storage database schedule --interval $(AUTOMATION_INTERVAL_HOURS) --sources $(AUTOMATION_SOURCES) --cities $(AUTOMATION_CITIES)

db-init:
	$(PYTHON) scripts/seed_db.py --init

seed-db:
	$(PYTHON) scripts/seed_db.py --seed

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

scheduler: scrape-automation-hourly
