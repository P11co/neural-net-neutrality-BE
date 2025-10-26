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
    """Fetch top 5 articles from InsForge database"""
    print("📰 Fetching top 5 articles from InsForge...")

    # Fetch directly from database via REST API
    import httpx

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(
            f"{INSFORGE_BASE_URL}/rest/v1/news_articles",
            headers=headers,
            params={
                "select": "id,title,content,summary,url,published_at,news_sources(id,name)",
                "order": "published_at.desc",
                "limit": "5"
            }
        )
        response.raise_for_status()
        articles = response.json()

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


def generate_audio_bytes(script: str) -> bytes:
    """Generate audio from script using ElevenLabs TTS and return as bytes"""
    print("🎙️ Generating audio with ElevenLabs...")

    voice_id = "UgBBYS2sOqTuMpoF3BR0"  # Professional news anchor voice
    model_id = "eleven_multilingual_v2"

    # Generate audio using ElevenLabs SDK
    audio_stream = elevenlabs_client.text_to_speech.convert(
        text=script,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128"
    )

    # Collect all chunks into bytes
    audio_bytes = b""
    for chunk in audio_stream:
        audio_bytes += chunk

    print(f"✓ Audio generated ({len(audio_bytes)} bytes)")
    return audio_bytes


async def upload_audio_to_insforge(audio_bytes: bytes) -> str:
    """Upload audio bytes directly to InsForge Storage and return public URL"""
    print("☁️ Uploading to InsForge Storage...")

    # InsForge Storage bucket name
    bucket_name = "podcast-episodes"

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    storage_filename = f"{timestamp}.mp3"

    # Upload using httpx
    import httpx
    from io import BytesIO

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
    }

    # Create file-like object from bytes
    audio_file = BytesIO(audio_bytes)
    files = {"file": (storage_filename, audio_file, "audio/mpeg")}

    async with httpx.AsyncClient(timeout=120.0) as http_client:
        response = await http_client.post(
            f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects/{storage_filename}",
            headers=headers,
            files=files
        )

        if response.status_code not in [200, 201]:
            print(f"Upload failed: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {response.text}")

    # Get public URL
    public_url = f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects/{storage_filename}"

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

        # Step 3: Generate audio (directly to bytes, no local file)
        audio_bytes = generate_audio_bytes(script)

        # Step 4: Upload to InsForge Storage (stream directly from memory)
        audio_url = await upload_audio_to_insforge(audio_bytes)

        # Step 5: Get audio duration (rough estimate from size)
        # More accurate duration would require audio analysis library
        audio_size_mb = len(audio_bytes) / (1024 * 1024)
        estimated_duration_seconds = int(audio_size_mb * 60)  # Rough estimate: 1MB ≈ 1 minute

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
    """Get list of podcast episodes from InsForge storage bucket"""
    import httpx
    import re
    from datetime import datetime

    print("📡 Fetching podcast episodes from InsForge storage...")

    # Fetch files from storage bucket
    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    bucket_name = "podcast-episodes"

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # List all files in the bucket
            response = await http_client.get(
                f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects",
                headers=headers
            )

            if response.status_code != 200:
                print(f"Storage fetch failed: {response.status_code} - {response.text}")
                return {"episodes": [], "count": 0}

            result = response.json()
            files = result.get("data", [])
            print(f"✓ Found {len(files)} files in storage")

            # Convert storage files to episode format
            episodes = []
            for file in files:
                file_name = file.get("key", "")

                # Skip non-mp3 files
                if not file_name.endswith(".mp3"):
                    continue

                # Parse date from filename (format: YYYY-MM-DD or YYYYMMDD)
                date_match = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', file_name)
                if date_match:
                    year, month, day = date_match.groups()
                    publication_date = f"{year}-{month}-{day}"
                    formatted_date = datetime.strptime(publication_date, "%Y-%m-%d")
                else:
                    # Fallback to file upload date
                    uploaded_at = file.get("uploaded_at", "") or file.get("uploadedAt", "")
                    if uploaded_at:
                        formatted_date = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                        publication_date = formatted_date.strftime("%Y-%m-%d")
                    else:
                        publication_date = datetime.now().strftime("%Y-%m-%d")
                        formatted_date = datetime.now()

                # Generate episode metadata
                episode_title = f"Daily Brief - {formatted_date.strftime('%B %d, %Y')}"

                # Use the URL from response or construct it
                audio_url = file.get("url") or f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects/{file_name}"

                # Get duration from file size (rough: 1MB ≈ 1 minute at 128kbps)
                file_size = file.get("size", 0)
                estimated_duration = int(file_size / (1024 * 1024) * 60) if file_size else 0

                episode = {
                    "id": file.get("id", file_name),  # Use file ID or name as episode ID
                    "title": episode_title,
                    "description": "Your daily AI-generated neutral news podcast covering the latest in AI and politics",
                    "publication_date": publication_date,
                    "audio_url": audio_url,
                    "duration_seconds": estimated_duration,
                    "cover_image_url": "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=800",
                    "play_count": 0
                }
                episodes.append(episode)

            # Sort by date (newest first)
            episodes.sort(key=lambda x: x["publication_date"], reverse=True)

            # Apply limit
            episodes = episodes[:limit]

            print(f"✓ Returning {len(episodes)} episodes")
            return {"episodes": episodes, "count": len(episodes)}

    except Exception as e:
        print(f"❌ Error fetching episodes: {e}")
        return {"episodes": [], "count": 0}


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
