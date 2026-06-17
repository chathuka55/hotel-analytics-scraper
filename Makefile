.PHONY: help install install-dev test test-cov lint format clean docker-build docker-run run scrape-booking scrape-agoda scrape-expedia scrape-sltda scrape-datagovlk run-all db-init seed-db docs

PYTHON := python
PIP := pip
VENV := venv

help:
	@echo "Hotel Scraper - Available Commands:"
	@echo ""
	@echo "  make install         Install production dependencies"
	@echo "  make install-dev     Install with dev dependencies"
	@echo "  make test            Run all tests"
	@echo "  make test-cov        Run tests with coverage"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make lint            Run linters (ruff, mypy)"
	@echo "  make format          Format code (black, ruff)"
	@echo "  make clean           Remove cache and temp files"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run Docker container"
	@echo "  make run             Run main CLI"
	@echo "  make scrape-booking  Run Booking.com scraper"
	@echo "  make scrape-agoda    Run Agoda.com scraper"
	@echo "  make scrape-expedia  Run Expedia.com scraper"
	@echo "  make scrape-sltda    Run SLTDA scraper"
	@echo "  make scrape-datagovlk Run data.gov.lk scraper"
	@echo "  make run-all         Run all scrapers"
	@echo "  make db-init         Initialize database"
	@echo "  make seed-db         Seed database with sample data"
	@echo "  make api             Run FastAPI server"
	@echo "  make scheduler       Run scheduler daemon"

install:
	$(PIP) install -r requirements.txt
	playwright install chromium

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev,api]"
	playwright install chromium

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
	docker run --rm --env-file .env hotel-scraper:latest

run:
	$(PYTHON) -m src.main

scrape-booking:
	$(PYTHON) -m src.main scrape --source booking --city Colombo

scrape-agoda:
	$(PYTHON) -m src.main scrape --source agoda --city Colombo

scrape-expedia:
	$(PYTHON) -m src.main scrape --source expedia --city Colombo

scrape-sltda:
	$(PYTHON) -m src.main scrape --source sltda

scrape-datagovlk:
	$(PYTHON) -m src.main scrape --source datagovlk

run-all:
	bash scripts/run_all.sh

db-init:
	$(PYTHON) scripts/seed_db.py --init

seed-db:
	$(PYTHON) scripts/seed_db.py --seed

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

scheduler:
	$(PYTHON) -m src.main schedule
