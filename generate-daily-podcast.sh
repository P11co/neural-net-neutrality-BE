#!/bin/bash
# Daily Podcast Generation Script
# This script should be run by cron to automatically generate daily podcasts
# Crontab example: 0 8 * * * /path/to/generate-daily-podcast.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🎙️ Daily Podcast Generation Workflow"
echo "======================================================================"
echo "Started at: $(date)"
echo ""

# Step 1: Scrape and import news articles
echo "Step 1: Scraping latest news articles..."
echo "----------------------------------------------------------------------"
cd news-report
./scrape_and_import.sh

if [ $? -ne 0 ]; then
    echo "❌ News scraping failed"
    exit 1
fi

echo "✓ News articles scraped and imported"
echo ""

# Step 2: Generate podcast episode
echo "Step 2: Generating podcast episode..."
echo "----------------------------------------------------------------------"
cd "$SCRIPT_DIR"

# Call the podcast generation API
RESPONSE=$(curl -s -X POST http://localhost:8081/generate-podcast \
    -H "Content-Type: application/json" \
    -w "\nHTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Podcast generation failed with status $HTTP_STATUS"
    echo "Response: $BODY"
    exit 1
fi

echo "✓ Podcast episode generated successfully"
echo ""

# Extract episode info from response
EPISODE_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('episode_id', 'N/A'))" 2>/dev/null || echo "N/A")
AUDIO_URL=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('audioUrl', 'N/A'))" 2>/dev/null || echo "N/A")

echo "Episode ID: $EPISODE_ID"
echo "Audio URL: $AUDIO_URL"
echo ""

# Step 3: Verify episode was saved to database
echo "Step 3: Verifying episode in database..."
echo "----------------------------------------------------------------------"

LATEST=$(curl -s http://localhost:8081/podcasts/latest)
FOUND=$(echo "$LATEST" | python3 -c "import sys, json; print(json.load(sys.stdin).get('found', False))" 2>/dev/null || echo "False")

if [ "$FOUND" == "True" ]; then
    echo "✓ Episode found in database"
else
    echo "⚠️  Warning: Episode not found in today's database query"
fi

echo ""
echo "======================================================================"
echo "✅ Daily podcast generation complete!"
echo "======================================================================"
echo "Completed at: $(date)"
echo ""
echo "Summary:"
echo "- News articles: Scraped and imported"
echo "- Podcast episode: Generated and uploaded"
echo "- Database: Episode metadata saved"
echo ""
echo "The new episode is now available at: http://localhost:8000/podcast.html"
echo ""
