/**
 * API Endpoint: Generate News Anchor Script
 *
 * GET /api/generate-news-script
 *
 * Fetches top 5 articles from InsForge and generates a news anchor script using LLM
 */

const { createClient } = require('@insforge/sdk');

// InsForge configuration
const INSFORGE_BASE_URL = process.env.INSFORGE_BASE_URL || "https://sv7kpi43.us-east.insforge.app";
const INSFORGE_API_KEY = process.env.INSFORGE_API_KEY || "ik_194453edb70ffcd51d76e2718b3f9eed";

// Create InsForge client
const client = createClient({
  baseUrl: INSFORGE_BASE_URL,
  anonKey: INSFORGE_API_KEY  // Use anonKey for anonymous access
});

/**
 * Format articles into a news anchor script prompt
 */
function createNewsPrompt(articles) {
  const articlesText = articles
    .map((article, index) => {
      return `
Story ${index + 1}: ${article.title}
Source: ${article.news_sources?.name || 'Unknown'}
Content: ${article.content || article.summary || 'No content available'}
---
`;
    })
    .join('\n');

  return `You are a professional news anchor creating a 2-3 minute broadcast script.

Create a natural, engaging news broadcast from these ${articles.length} top stories:

${articlesText}

Requirements:
- Start with a warm greeting and introduction
- Present each story in a conversational, professional tone
- Use smooth transitions between stories
- Keep it concise but informative
- End with a brief closing statement
- Make it sound natural when spoken aloud
- Total length: approximately 2-3 minutes when read aloud

Write the complete script now:`;
}

/**
 * Main handler
 */
module.exports = async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle OPTIONS preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Only allow GET
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    console.log('📰 Fetching top 5 articles from InsForge...');

    // Step 1: Query InsForge for top 5 most recent articles
    const { data: articles, error: fetchError } = await client.database
      .from('news_articles')
      .select('*, news_sources(name)')
      .order('published_at', { ascending: false })
      .limit(5);

    if (fetchError) {
      console.error('Error fetching articles:', fetchError);
      return res.status(500).json({
        error: 'Failed to fetch articles',
        details: fetchError.message
      });
    }

    if (!articles || articles.length === 0) {
      return res.status(404).json({
        error: 'No articles found in database',
        message: 'Please run the scraper first to populate articles'
      });
    }

    console.log(`✓ Found ${articles.length} articles`);

    // Step 2: Create the prompt
    const prompt = createNewsPrompt(articles);

    console.log('🤖 Generating news anchor script with GPT-5-mini...');

    // Step 3: Generate script using InsForge AI API (GPT-5-mini)
    const completion = await client.ai.chat.completions.create({
      model: 'openai/gpt-5-mini',
      messages: [
        {
          role: 'system',
          content: 'You are a professional news anchor with years of experience in broadcast journalism. Create engaging, clear, and professional news scripts.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.7,
      maxTokens: 1500
    });

    const script = completion.choices[0].message.content;

    console.log('✓ Script generated successfully');

    // Step 4: Return the result
    return res.status(200).json({
      success: true,
      script: script,
      articles: articles.map(a => ({
        id: a.id,
        title: a.title,
        source: a.news_sources?.name || 'Unknown',
        published_at: a.published_at,
        url: a.url
      })),
      metadata: {
        articlesCount: articles.length,
        model: 'gpt-5-mini',
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('❌ Error generating news script:', error);

    return res.status(500).json({
      success: false,
      error: 'Failed to generate news script',
      details: error.message
    });
  }
};
