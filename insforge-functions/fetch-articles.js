// InsForge Edge Function: Fetch latest news articles
// This function fetches the top 5 most recent articles with their sources

module.exports = async function(request) {
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  // Handle OPTIONS request
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders
    });
  }

  try {
    // Extract token from request (if provided)
    const authHeader = request.headers.get('Authorization');
    const userToken = authHeader ? authHeader.replace('Bearer ', '') : null;

    // Get anon key from environment
    const anonKey = Deno.env.get('ACCESS_API_KEY');

    // Create client with appropriate token
    const client = createClient({
      baseUrl: Deno.env.get('BACKEND_INTERNAL_URL') || 'http://insforge:7130',
      anonKey: userToken || anonKey
    });

    // Parse query parameters
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '5');

    // Fetch articles with source information
    const { data: articles, error } = await client.database
      .from('news_articles')
      .select(`
        id,
        title,
        content,
        summary,
        url,
        published_at,
        news_sources (
          id,
          name
        )
      `)
      .order('published_at', { ascending: false })
      .limit(limit);

    if (error) {
      return new Response(
        JSON.stringify({
          error: error.message,
          details: error
        }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Format response to match expected structure
    const formattedArticles = articles.map(article => ({
      id: article.id,
      title: article.title,
      content: article.content || article.summary || '',
      url: article.url,
      published_at: article.published_at,
      news_sources: article.news_sources
    }));

    return new Response(
      JSON.stringify({
        success: true,
        count: formattedArticles.length,
        articles: formattedArticles
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );

  } catch (err) {
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        message: err.message
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
};
