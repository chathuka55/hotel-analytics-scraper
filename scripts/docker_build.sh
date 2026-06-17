#!/usr/bin/env bash
# Build and run Docker container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Building Hotel Scraper Docker image..."

docker build -t hotel-scraper:latest .

echo ""
echo "Docker image built successfully!"
echo ""
echo "To run:"
echo "  docker run --rm --env-file .env hotel-scraper:latest"
echo ""
echo "To run with volume for data:"
echo "  docker run --rm --env-file .env -v \$(pwd)/data:/app/data hotel-scraper:latest"
