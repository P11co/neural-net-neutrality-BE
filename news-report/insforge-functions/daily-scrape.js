/**
 * InsForge Edge Function for Daily News Scraping
 *
 * This runs as a Deno edge function on InsForge
 * Can be triggered by external cron services like cron-job.org or EasyCron
 *
 * Deploy with:
 * API_BASE_URL="https://sv7kpi43.us-east.insforge.app" npx -y @insforge/mcp@latest --api_key "ik_194453edb70ffcd51d76e2718b3f9eed" << 'EOF'
 * {"jsonrpc":"2.0","method":"tools/call","params":{"name":"create-function","arguments":{"name":"Daily News Scraper","slug":"daily-scrape","codeFile":"backend/news-report/insforge-functions/daily-scrape.js"}},"id":15}
 * EOF
 */

// InsForge automatically provides createClient
module.exports = async function(request) {
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  // Handle OPTIONS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  // Simple authentication check
  const CRON_SECRET = Deno.env.get('CRON_SECRET') || 'your-secret-key-here';
  const authHeader = request.headers.get('Authorization');

  if (authHeader !== `Bearer ${CRON_SECRET}`) {
    return new Response(
      JSON.stringify({ error: 'Unauthorized' }),
      {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }

  console.log('🚀 Starting daily news scrape...');

  try {
    // Configuration
    const BRIGHTDATA_API_TOKEN = Deno.env.get('BRIGHTDATA_API_TOKEN');
    const COLLECTOR_ID = 'c_mh63scdem3jiaigq0';

    if (!BRIGHTDATA_API_TOKEN) {
      throw new Error('BRIGHTDATA_API_TOKEN not configured');
    }

    // News sources
    const sources = [
      { name: 'BBC', url: 'https://www.bbc.com/', id: '969e05ab-1549-4c61-a7ad-accff1f0eb5f' },
      { name: 'Reuters', url: 'https://www.reuters.com/', id: '6cf6e9c0-a4b4-41be-8071-c74b722101e8' },
      { name: 'Straight Arrow News', url: 'https://www.straightarrownews.com/', id: '8bfc9d71-b0ec-43be-a899-818bad04a684' }
    ];

    const results = [];

    // Trigger scrapers for each source
    for (const source of sources) {
      console.log(`Triggering scraper for ${source.name}...`);

      // Trigger Bright Data scraper
      const triggerResponse = await fetch(
        `https://api.brightdata.com/dca/trigger?queue_next=1&collector=${COLLECTOR_ID}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${BRIGHTDATA_API_TOKEN}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify([{ url: source.url }])
        }
      );

      if (!triggerResponse.ok) {
        throw new Error(`Failed to trigger scraper for ${source.name}: ${triggerResponse.statusText}`);
      }

      const triggerData = await triggerResponse.json();
      const snapshotId = triggerData.snapshot_id;

      console.log(`${source.name} snapshot ID: ${snapshotId}`);

      // Wait for completion and import (simplified - in production use polling)
      results.push({
        source: source.name,
        snapshotId: snapshotId,
        status: 'triggered'
      });
    }

    // Note: In a real implementation, you'd need to:
    // 1. Poll for completion
    // 2. Download the JSON results
    // 3. Import to database
    //
    // This is complex for an edge function, so it's better to:
    // - Use GitHub Actions (recommended)
    // - Or have this edge function trigger a webhook to a service that does the full workflow

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Scraping jobs triggered successfully',
        timestamp: new Date().toISOString(),
        results: results
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );

  } catch (error) {
    console.error('Error in daily scrape:', error);

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
};
