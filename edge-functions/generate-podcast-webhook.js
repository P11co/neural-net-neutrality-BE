/**
 * InsForge Edge Function: Podcast Generation Webhook Handler
 *
 * Triggered by Bright Data webhook after daily scraping completes
 * Orchestrates: Script Generation → Audio Generation → Storage Upload → Database Save
 *
 * Deploy with: insforge edge-function create
 * Webhook URL: https://{PROJECT}.insforge.app/functions/v1/generate-podcast-webhook
 */

// Environment variables (set in InsForge dashboard)
const INSFORGE_BASE_URL = Deno.env.get("INSFORGE_BASE_URL");
const INSFORGE_API_KEY = Deno.env.get("INSFORGE_API_KEY");
const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY");
const ELEVENLABS_API_KEY = Deno.env.get("ELEVENLABS_API_KEY");

const BUCKET_NAME = "podcast-episodes";
const VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"; // Professional news anchor voice

module.exports = async function(request) {
  console.log("🚀 Podcast generation webhook triggered");

  // Only accept POST requests
  if (request.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "Method not allowed" }),
      { status: 405, headers: { "Content-Type": "application/json" } }
    );
  }

  try {
    // Step 1: Fetch latest articles from database
    console.log("📰 Fetching articles from InsForge database...");
    const articles = await fetchArticles();

    if (!articles || articles.length === 0) {
      console.error("❌ No articles found in database");
      return new Response(
        JSON.stringify({
          error: "No articles found",
          message: "Scraper may not have run yet or no articles exist"
        }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }
    console.log(`✓ Found ${articles.length} articles`);

    // Step 2: Generate script with OpenAI
    console.log("🤖 Generating script with OpenAI...");
    const script = await generateScript(articles);
    console.log(`✓ Script generated (${script.length} chars)`);

    // Step 3: Generate audio with ElevenLabs
    console.log("🎙️ Generating audio with ElevenLabs...");
    const audioBlob = await generateAudio(script);
    console.log(`✓ Audio generated (${audioBlob.size} bytes)`);

    // Step 4: Upload to InsForge Storage
    console.log("☁️ Uploading to InsForge Storage...");
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `daily-brief-${timestamp}.mp3`;
    const audioUrl = await uploadToStorage(audioBlob, filename);
    console.log(`✓ Uploaded to ${audioUrl}`);

    // Step 5: Save episode metadata to database
    console.log("💾 Saving episode to database...");
    const duration = estimateDuration(audioBlob.size);
    const episode = await saveEpisode({
      audioUrl,
      script,
      articles,
      duration,
      filename
    });
    console.log(`✓ Episode saved with ID: ${episode.id}`);

    // Step 6: Return success response
    console.log("✅ Podcast generation complete!");
    return new Response(
      JSON.stringify({
        success: true,
        episode: {
          id: episode.id,
          audioUrl,
          duration,
          articlesCount: articles.length,
          generatedAt: new Date().toISOString()
        }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("❌ Error generating podcast:", error);
    return new Response(
      JSON.stringify({
        error: "Podcast generation failed",
        message: error.message,
        stack: error.stack
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
};

/**
 * Fetch top 5 articles from InsForge database
 */
async function fetchArticles() {
  const response = await fetch(
    `${INSFORGE_BASE_URL}/rest/v1/news_articles`,
    {
      headers: {
        "apikey": INSFORGE_API_KEY,
        "Authorization": `Bearer ${INSFORGE_API_KEY}`
      },
      params: new URLSearchParams({
        select: "id,title,content,summary,url,published_at,news_sources(id,name)",
        order: "published_at.desc",
        limit: "5"
      })
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch articles: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Generate news script using OpenAI GPT-5-mini
 */
async function generateScript(articles) {
  // Format articles into prompt
  let articlesText = "";
  articles.forEach((article, i) => {
    const source = article.news_sources?.name || "Unknown";
    const content = article.content || article.summary || "No content available";
    articlesText += `\nStory ${i + 1}: ${article.title}\nSource: ${source}\nContent: ${content}\n---\n`;
  });

  const prompt = `You are a professional news anchor creating a 2-3 minute broadcast script.

Create a politically neutral, natural and engaging news broadcast from these ${articles.length} top stories:

${articlesText}

Requirements:
- Start with a warm greeting and introduction (Your company: Neutral Network)
- This is a monologue, so never need to label who is saying what (i.e. no need to say Anchor: text, just say text)
- No settings or exposition (no need to say intro music, outro music, etc.)
- Present each story in a conversational, professional tone
- Use smooth transitions between stories
- Keep it concise but informative
- End with a brief closing statement

The complete script`;

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${OPENAI_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: "gpt-5-mini",
      messages: [
        {
          role: "system",
          content: "You are a professional news anchor with years of experience in broadcast journalism. Create engaging, clear, and professional news scripts."
        },
        {
          role: "user",
          content: prompt
        }
      ]
    })
  });

  if (!response.ok) {
    throw new Error(`OpenAI API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.choices[0].message.content;
}

/**
 * Generate audio from script using ElevenLabs TTS
 */
async function generateAudio(script) {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`,
    {
      method: "POST",
      headers: {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text: script,
        model_id: "eleven_multilingual_v2",
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75
        }
      })
    }
  );

  if (!response.ok) {
    throw new Error(`ElevenLabs API error: ${response.status} ${response.statusText}`);
  }

  return await response.blob();
}

/**
 * Upload audio blob to InsForge Storage
 */
async function uploadToStorage(audioBlob, filename) {
  const formData = new FormData();
  formData.append("file", audioBlob, filename);

  const response = await fetch(
    `${INSFORGE_BASE_URL}/api/storage/buckets/${BUCKET_NAME}/objects/${filename}`,
    {
      method: "POST",
      headers: {
        "apikey": INSFORGE_API_KEY,
        "Authorization": `Bearer ${INSFORGE_API_KEY}`
      },
      body: formData
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Storage upload failed: ${response.status} - ${error}`);
  }

  // Return public URL
  return `${INSFORGE_BASE_URL}/api/storage/buckets/${BUCKET_NAME}/objects/${filename}`;
}

/**
 * Save episode metadata to podcast_episodes table
 */
async function saveEpisode({ audioUrl, script, articles, duration, filename }) {
  const today = new Date().toISOString().split('T')[0];
  const title = `Daily Brief - ${new Date().toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  })}`;

  const payload = {
    title,
    description: `Your daily AI-generated neutral news podcast for ${today}`,
    publication_date: today,
    audio_url: audioUrl,
    duration_seconds: duration,
    script,
    article_ids: articles.map(a => a.id)
  };

  const response = await fetch(
    `${INSFORGE_BASE_URL}/rest/v1/podcast_episodes`,
    {
      method: "POST",
      headers: {
        "apikey": INSFORGE_API_KEY,
        "Authorization": `Bearer ${INSFORGE_API_KEY}`,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Database save failed: ${response.status} - ${error}`);
  }

  const data = await response.json();
  return Array.isArray(data) ? data[0] : data;
}

/**
 * Estimate duration from audio file size
 * Rough calculation: 1MB ≈ 1 minute at 128kbps MP3
 */
function estimateDuration(sizeBytes) {
  const sizeMB = sizeBytes / (1024 * 1024);
  return Math.round(sizeMB * 60);
}
