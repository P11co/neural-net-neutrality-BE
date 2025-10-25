#!/bin/bash
# Complete workflow: Scrape news from Bright Data and import to InsForge
# Usage: ./scrape_and_import.sh

set -e  # Exit on error

echo "======================================================================"
echo "📰 News Scraping and Import Workflow"
echo "======================================================================"
echo ""

# Check for required environment variables
if [ -z "$BRIGHTDATA_API_TOKEN" ]; then
    echo "❌ Error: BRIGHTDATA_API_TOKEN environment variable not set"
    echo "Please set it with: export BRIGHTDATA_API_TOKEN='your_token_here'"
    exit 1
fi

# Change to script directory
cd "$(dirname "$0")"

echo "Step 1: Trigger Bright Data scrapers and download results"
echo "----------------------------------------------------------------------"
python3 trigger_brightdata_scraper.py

# Check if scraping was successful
if [ $? -ne 0 ]; then
    echo "❌ Scraping failed"
    exit 1
fi

echo ""
echo "Step 2: Import scraped data into InsForge"
echo "----------------------------------------------------------------------"

# Find all JSON files in data/ directory from today
TODAY=$(date +%Y%m%d)

# Import each file
for file in data/*_${TODAY}_*.json; do
    if [ -f "$file" ]; then
        # Extract source name from filename
        # e.g., "data/bbc_20251025_123456.json" -> "BBC"
        basename=$(basename "$file")

        if [[ $basename == bbc_* ]]; then
            SOURCE="BBC"
        elif [[ $basename == reuters_* ]]; then
            SOURCE="Reuters"
        elif [[ $basename == straight_arrow_news_* ]]; then
            SOURCE="Straight Arrow News"
        else
            echo "⚠ Unknown source for file: $file, skipping"
            continue
        fi

        echo ""
        echo "Importing $SOURCE from $file..."
        node import_brightdata_to_insforge.js "$file" "$SOURCE"

        if [ $? -eq 0 ]; then
            echo "✓ Successfully imported $SOURCE"
        else
            echo "✗ Failed to import $SOURCE"
        fi
    fi
done

echo ""
echo "======================================================================"
echo "✅ Workflow complete!"
echo "======================================================================"
echo ""
echo "Your news database is now updated with the latest articles."
echo "You can query them from your InsForge backend at:"
echo "https://sv7kpi43.us-east.insforge.app"
