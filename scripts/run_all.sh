#!/usr/bin/env bash
# Run all scrapers sequentially

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "Hotel Scraper - Running All Sources"
echo "Started: $(date)"
echo "=========================================="

if [ -f .env ]; then
    source .env
fi

PYTHON="${PYTHON:-python}"
SOURCES=(
  "booking" "agoda" "expedia"
  "skyscanner" "rehlat" "traveloka" "tripadvisor" "tripcom" "goseek" "etrip" "hotelscom"
  "sltda" "datagovlk"
)
CITIES=("Colombo" "Kandy" "Galle")
FAILED=()
SUCCESS=()

for source in "${SOURCES[@]}"; do
    echo ""
    echo "------------------------------------------"
    echo "Scraping: $source"
    echo "------------------------------------------"

    if [ "$source" == "sltda" ] || [ "$source" == "datagovlk" ]; then
        if $PYTHON -m src.main scrape --source "$source" --storage database; then
            SUCCESS+=("$source")
            echo "✓ $source completed"
        else
            FAILED+=("$source")
            echo "✗ $source failed"
        fi
    else
        for city in "${CITIES[@]}"; do
            echo ""
            echo "City: $city"
            if $PYTHON -m src.main scrape \
                --source "$source" \
                --city "$city" \
                --max-pages 2 \
                --storage database; then
                echo "✓ $source - $city completed"
            else
                echo "✗ $source - $city failed"
            fi
            sleep 5
        done
        SUCCESS+=("$source")
    fi

    sleep 10
done

echo ""
echo "Purging unknown/junk records..."
$PYTHON -m src.main --storage database purge-unknown || true

echo ""
echo "=========================================="
echo "Run Complete: $(date)"
echo "=========================================="
echo "Successful: ${#SUCCESS[@]}"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo "Failed sources:"
    for f in "${FAILED[@]}"; do
        echo "  - $f"
    done
    exit 1
fi

echo ""
echo "All scrapers completed successfully!"
