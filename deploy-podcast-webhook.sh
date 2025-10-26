#!/bin/bash

###############################################################################
# Deploy Podcast Generation Webhook to InsForge Edge Functions
#
# This script deploys the edge function that handles the complete podcast
# generation flow when triggered by Bright Data webhook
###############################################################################

set -e  # Exit on error

echo "🚀 Deploying Podcast Generation Webhook to InsForge..."

# Check if InsForge CLI is installed
if ! command -v insforge &> /dev/null; then
    echo "❌ InsForge CLI not found. Install with:"
    echo "   npm install -g @insforge/cli"
    exit 1
fi

# Load environment variables
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

source .env

# Verify required environment variables
required_vars=(
    "INSFORGE_BASE_URL"
    "INSFORGE_API_KEY"
    "OPENAI_API_KEY"
    "ELEVENLABS_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing environment variable: $var"
        exit 1
    fi
done

echo "✓ Environment variables verified"

# Deploy edge function
echo "📦 Deploying edge function..."
cd edge-functions

insforge edge-function create \
    --name "generate-podcast-webhook" \
    --slug "generate-podcast-webhook" \
    --code-file "generate-podcast-webhook.js" \
    --description "Webhook handler for automated daily podcast generation" \
    --status "active"

echo "✅ Edge function deployed successfully!"
echo ""
echo "📋 Setup Instructions:"
echo "   1. Your webhook URL is:"
echo "      ${INSFORGE_BASE_URL}/functions/v1/generate-podcast-webhook"
echo ""
echo "   2. Configure Bright Data to POST to this URL after scraping completes"
echo ""
echo "   3. Set environment variables in InsForge dashboard:"
echo "      - INSFORGE_BASE_URL=${INSFORGE_BASE_URL}"
echo "      - INSFORGE_API_KEY=<your-key>"
echo "      - OPENAI_API_KEY=<your-key>"
echo "      - ELEVENLABS_API_KEY=<your-key>"
echo ""
echo "   4. Test the webhook:"
echo "      curl -X POST ${INSFORGE_BASE_URL}/functions/v1/generate-podcast-webhook"
echo ""
