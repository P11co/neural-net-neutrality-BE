"""
Podcast Generation API Endpoint

POST /generate-podcast
- Fetches top 5 articles from InsForge
- Generates news script with GPT-5-mini
- Converts to audio using ElevenLabs TTS
- Uploads to InsForge Storage
- Returns audio URL and metadata
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import hashlib

# Add news-report to path to import elevenlab module
sys.path.append(str(Path(__file__).parent / "news-report"))

from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings

# Load environment variables
load_dotenv(".env", override=True)

# InsForge configuration
INSFORGE_BASE_URL = os.getenv("INSFORGE_BASE_URL", "https://sv7kpi43.us-east.insforge.app")
INSFORGE_API_KEY = os.getenv("INSFORGE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Create InsForge client
try:
    from insforge import createClient

    client = createClient({
        "baseUrl": INSFORGE_BASE_URL,
        "anonKey": INSFORGE_API_KEY
    })
except ImportError:
    # Fallback to @insforge/sdk if Python SDK not available
    import subprocess
    import json
    client = None  # Will use Node.js CLI calls

# Create ElevenLabs client
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_news_prompt(articles):
    """Format articles into a news anchor script prompt"""
    articles_text = ""
    for i, article in enumerate(articles, 1):
        source = article.get("news_sources", {}).get("name", "Unknown") if isinstance(article.get("news_sources"), dict) else "Unknown"
        content = article.get("content") or article.get("summary") or "No content available"

        articles_text += f"""
            Story {i}: {article['title']}
            Source: {source}
            Content: {content}
            ---
            """

    return f"""You are a professional news anchor creating a 2-3 minute broadcast script.

        Create a politically neutral, natural and engaging news broadcast from these {len(articles)} top stories:

        {articles_text}

        Requirements:
        - Start with a warm greeting and introduction (Your company: Neutral Network)
        - This is a monologue, so never need to label who is saying what (i.e. no need to say Anchor: text, just say text)
        - No settings or exposition (no need to say intro music, outro music, etc.)
        - Present each story in a conversational, professional tone
        - Use smooth transitions between stories
        - Keep it concise but informative
        - End with a brief closing statement

        The complete script"""

async def fetch_articles():
    """Fetch top 5 articles from InsForge using the edge function"""
    print("📰 Fetching top 5 articles from InsForge...")

    # Use the deployed edge function to fetch articles
    import httpx

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
            f"{INSFORGE_BASE_URL}/functions/v1/fetch-articles",
            headers=headers,
            params={"limit": "5"}
        )
        response.raise_for_status()
        result = response.json()

        # The edge function returns {success, count, articles}
        articles = result.get("articles", [])

    print(f"✓ Found {len(articles)} articles")
    return articles


async def generate_script(articles):
    """Generate news script using OpenAI GPT-5-mini (cost-effective, high quality)"""
    print("🤖 Generating news anchor script with OpenAI GPT-5-mini...")

    prompt = create_news_prompt(articles)

    # Use OpenAI SDK directly (InsForge AI only available via JavaScript SDK)
    from openai import AsyncOpenAI

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = AsyncOpenAI(api_key=openai_key)

    response = await client.chat.completions.create(
        model="gpt-5-mini",  # Cost-effective alternative to gpt-5-mini
        messages=[
            {
                "role": "system",
                "content": "You are a professional news anchor with years of experience in broadcast journalism. Create engaging, clear, and professional news scripts."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
    )
    script = response.choices[0].message.content
    print("✓ Script generated successfully")
    return script


def generate_audio(script: str, output_path: Path = None) -> Path:
    """Generate audio from script using ElevenLabs TTS"""
    print("🎙️ Generating audio with ElevenLabs...")

    if output_path is None:
        # Create timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / "news-report" / "audio-data" / f"podcast_{timestamp}.mp3"

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate audio using ElevenLabs SDK
    voice_id = "UgBBYS2sOqTuMpoF3BR0"  # Professional news anchor voice
    model_id = "eleven_multilingual_v2"

    audio_stream = elevenlabs_client.text_to_speech.convert(
        text=script,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128"
    )

    # Write stream to file
    with output_path.open("wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

    print(f"✓ Audio saved to {output_path}")
    return output_path


async def upload_to_insforge_storage(file_path: Path) -> str:
    """Upload audio file to InsForge Storage and return public URL"""
    print("☁️ Uploading to InsForge Storage...")

    # InsForge Storage bucket name
    bucket_name = "podcast-episodes"

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    storage_filename = f"{timestamp}.mp3"

    # Upload using httpx
    import httpx

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
    }

    with file_path.open("rb") as f:
        files = {"file": (storage_filename, f, "audio/mpeg")}

        async with httpx.AsyncClient(timeout=120.0) as http_client:
            response = await http_client.post(
                f"{INSFORGE_BASE_URL}/storage/v1/object/{bucket_name}/{storage_filename}",
                headers=headers,
                files=files
            )

            if response.status_code not in [200, 201]:
                print(f"Upload failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {response.text}")

    # Get public URL
    public_url = f"{INSFORGE_BASE_URL}/storage/v1/object/public/{bucket_name}/{storage_filename}"

    print(f"✓ Uploaded to {public_url}")
    return public_url


@app.post("/generate-podcast")
async def generate_podcast():
    """
    Generate a complete podcast episode:
    1. Fetch articles
    2. Generate script
    3. Convert to audio
    4. Upload to storage
    5. Return metadata
    """
    try:
        # Step 1: Fetch articles
        articles = await fetch_articles()

        if not articles or len(articles) == 0:
            raise HTTPException(
                status_code=404,
                detail="No articles found. Please run the scraper first."
            )

        # Step 2: Generate script
        script = await generate_script(articles)

        # Step 3: Generate audio
        audio_file = generate_audio(script)

        # Step 4: Upload to InsForge Storage
        audio_url = await upload_to_insforge_storage(audio_file)

        # Step 5: Get audio duration (rough estimate from file size)
        # More accurate duration would require audio analysis library
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        estimated_duration_seconds = int(file_size_mb * 60)  # Rough estimate: 1MB ≈ 1 minute

        # Clean up local file (optional - keep for backup)
        # audio_file.unlink()

        # Step 6: Save to database
        articles_formatted = [
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "source": a.get("news_sources", {}).get("name", "Unknown") if isinstance(a.get("news_sources"), dict) else "Unknown",
                "published_at": a.get("published_at"),
                "url": a.get("url")
            }
            for a in articles
        ]

        episode_db_entry = await save_episode_to_database(
            audio_url=audio_url,
            script=script,
            articles=articles,
            duration=estimated_duration_seconds
        )

        # Step 7: Format response
        response_data = {
            "success": True,
            "audioUrl": audio_url,
            "script": script,
            "duration": estimated_duration_seconds,
            "articles": articles_formatted,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": "gpt-5-mini",
                "voice": "ElevenLabs - Professional Anchor",
                "articles_count": len(articles)
            }
        }

        if episode_db_entry:
            response_data["episode_id"] = episode_db_entry.get("id")

        print("✅ Podcast generated successfully!")
        return response_data

    except Exception as e:
        print(f"❌ Error generating podcast: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate podcast: {str(e)}"
        )


async def save_episode_to_database(audio_url: str, script: str, articles: list, duration: int) -> dict:
    """Save episode metadata to InsForge podcast_episodes table"""
    print("💾 Saving episode to database...")

    import httpx

    today = datetime.now().date().isoformat()
    title = f"Daily Brief - {datetime.now().strftime('%B %d, %Y')}"

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # Extract article IDs
    article_ids = [a.get("id") for a in articles if a.get("id")]

    payload = {
        "title": title,
        "description": f"Your daily AI-generated neutral news podcast for {today}",
        "publication_date": today,
        "audio_url": audio_url,
        "duration_seconds": duration,
        "script": script,
        "article_ids": article_ids
    }

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            f"{INSFORGE_BASE_URL}/rest/v1/podcast_episodes",
            headers=headers,
            json=payload
        )

        if response.status_code not in [200, 201]:
            print(f"Database save failed: {response.status_code} - {response.text}")
            # Don't fail the whole request if DB save fails
            return None

        episode_data = response.json()

    print(f"✓ Episode saved to database")
    return episode_data[0] if isinstance(episode_data, list) else episode_data


@app.get("/podcasts")
async def get_podcasts(limit: int = 10):
    """Get list of podcast episodes"""
    import httpx

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
            f"{INSFORGE_BASE_URL}/rest/v1/podcast_episodes",
            headers=headers,
            params={
                "select": "id,title,description,publication_date,audio_url,duration_seconds,cover_image_url,play_count",
                "order": "publication_date.desc",
                "limit": limit
            }
        )
        response.raise_for_status()
        episodes = response.json()

    return {"episodes": episodes, "count": len(episodes)}


@app.get("/podcasts/latest")
async def get_latest_podcast():
    """Get today's podcast episode"""
    import httpx

    today = datetime.now().date().isoformat()

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
            f"{INSFORGE_BASE_URL}/rest/v1/podcast_episodes",
            headers=headers,
            params={
                "publication_date": f"eq.{today}",
                "select": "*",
                "limit": 1
            }
        )

        if response.status_code == 200:
            episodes = response.json()
            if episodes and len(episodes) > 0:
                return {"episode": episodes[0], "found": True}

    return {"episode": None, "found": False, "message": "No episode for today yet"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "podcast-generator",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081, reload=True)
