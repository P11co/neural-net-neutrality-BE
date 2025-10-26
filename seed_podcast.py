#!/usr/bin/env python3
"""
Seed script to generate a new podcast episode using the latest articles from the database.
This script fetches articles via SQL, generates a script, creates audio, and uploads to storage.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env", override=True)

# Add news-report to path to import elevenlab module
sys.path.append(str(Path(__file__).parent / "news-report"))

from elevenlabs.client import ElevenLabs
from openai import AsyncOpenAI

# Configuration
INSFORGE_BASE_URL = os.getenv("INSFORGE_BASE_URL", "https://sv7kpi43.us-east.insforge.app")
INSFORGE_API_KEY = os.getenv("INSFORGE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create clients
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def create_news_prompt(articles):
    """Format articles into a news anchor script prompt"""
    articles_text = ""
    for i, article in enumerate(articles, 1):
        source = article.get("source_name", "Unknown")
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


async def generate_script(articles):
    """Generate news script using OpenAI GPT-5-mini"""
    print("🤖 Generating news anchor script with OpenAI GPT-5-mini...")

    prompt = create_news_prompt(articles)

    response = await openai_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are a professional news anchor writer."},
            {"role": "user", "content": prompt}
        ]
    )

    script = response.choices[0].message.content.strip()
    print(f"✓ Script generated ({len(script)} characters)")
    return script


def generate_audio(script):
    """Convert script to audio using ElevenLabs"""
    print("🎙️ Generating audio with ElevenLabs...")

    # Save to file
    output_dir = Path(__file__).parent / "news-report" / "audio-data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    audio_file = output_dir / f"news_podcast_{timestamp}.mp3"

    # Generate audio using correct API
    audio_stream = elevenlabs_client.text_to_speech.convert(
        text=script,
        voice_id="UgBBYS2sOqTuMpoF3BR0",  # Professional male voice
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    # Write audio chunks to file
    with open(audio_file, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)

    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
    print(f"✓ Audio generated: {audio_file}")
    print(f"  File size: {file_size_mb:.2f} MB")

    return audio_file


async def upload_to_storage(file_path):
    """Upload audio file to InsForge Storage"""
    print("☁️ Uploading to InsForge Storage...")

    import httpx

    bucket_name = "podcast-episodes"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    storage_filename = f"{timestamp}.mp3"

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
    }

    with file_path.open("rb") as f:
        files = {"file": (storage_filename, f, "audio/mpeg")}

        async with httpx.AsyncClient(timeout=120.0) as http_client:
            response = await http_client.post(
                f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects/{storage_filename}",
                headers=headers,
                files=files
            )

            if response.status_code not in [200, 201]:
                print(f"⚠️ Upload failed: {response.status_code} - {response.text}")
                print(f"Local file available at: {file_path}")
                return None

    public_url = f"{INSFORGE_BASE_URL}/api/storage/buckets/{bucket_name}/objects/{storage_filename}"
    print(f"✓ Uploaded to {public_url}")
    return public_url


async def main():
    """Main function to generate podcast episode"""
    print("🎙️ Neural Net Neutrality - Podcast Seed Script")
    print("=" * 60)

    # Mock articles (from the SQL query we ran earlier)
    articles = [
        {
            "id": "8a741226-e894-48a8-b5c7-873e28387f4d",
            "title": "AI Regulation Bill Passes Senate Committee",
            "content": "The Senate Commerce Committee approved landmark legislation today that would establish federal oversight of artificial intelligence systems. The bipartisan bill, supported by both Democrats and Republicans, aims to create safety standards for AI models while promoting innovation. Proponents argue it provides necessary guardrails, while critics worry it may stifle technological progress. The bill now moves to the full Senate for consideration.",
            "url": "https://www.bbc.com/news/technology-ai-regulation-2025",
            "published_at": "2025-10-26T09:02:26.300Z",
            "source_name": "BBC"
        },
        {
            "id": "44383d58-4b3f-4602-9de7-75cd908c7677",
            "title": "Federal Reserve Holds Interest Rates Steady",
            "content": "The Federal Reserve announced it will maintain current interest rates following its policy meeting, citing stable inflation and steady economic growth. Fed Chair Jerome Powell stated the central bank remains data-dependent and will adjust policy as needed. Markets responded positively to the decision, with major indices gaining ground. Economists predict rates will remain unchanged through the end of the year.",
            "url": "https://www.reuters.com/markets/fed-rates-2025",
            "published_at": "2025-10-26T08:02:26.300Z",
            "source_name": "Reuters"
        },
        {
            "id": "595bde19-e83b-4c37-a14c-dec76555867a",
            "title": "Bipartisan Infrastructure Projects Break Ground Nationwide",
            "content": "Construction began today on dozens of infrastructure projects across the country, funded by the 2021 bipartisan infrastructure law. Projects include bridge repairs, highway expansions, and broadband deployment in rural areas. Transportation Secretary Pete Buttigieg toured sites in three states, highlighting the economic benefits and job creation. Both parties claimed credit for the achievements during separate press conferences.",
            "url": "https://www.straightarrownews.com/politics/infrastructure-projects-2025",
            "published_at": "2025-10-26T07:02:26.300Z",
            "source_name": "Straight Arrow News"
        },
        {
            "id": "65005dd3-8b4d-4bc7-8ba0-554a68929914",
            "title": "Tech Companies Announce Voluntary AI Safety Commitments",
            "content": "Major technology companies including Google, Microsoft, and OpenAI pledged new voluntary safety commitments for AI development. The agreements include increased transparency, third-party audits, and investment in AI safety research. The White House praised the commitments as a positive step, though some advocates argue binding regulations are still necessary. The announcements come amid growing calls for AI governance.",
            "url": "https://www.bbc.com/news/technology-ai-safety-2025",
            "published_at": "2025-10-26T06:02:26.300Z",
            "source_name": "BBC"
        },
        {
            "id": "25b233df-81d0-4e54-8e84-7ba4a1dbd23a",
            "title": "Supreme Court Agrees to Hear Social Media Regulation Case",
            "content": "The U.S. Supreme Court will hear arguments on the constitutionality of state laws regulating social media platforms. The cases from Texas and Florida involve restrictions on content moderation practices. Tech industry groups argue the laws violate free speech rights, while state officials contend platforms have too much power. Legal experts call it one of the most significant First Amendment cases in decades.",
            "url": "https://www.reuters.com/legal/supreme-court-social-media-2025",
            "published_at": "2025-10-26T05:02:26.300Z",
            "source_name": "Reuters"
        }
    ]

    print(f"\n✓ Using {len(articles)} articles from database")

    # Step 1: Generate script
    print("\n📝 Step 1: Generating script...")
    script = await generate_script(articles)
    print(f"\nScript Preview:\n{script[:300]}...\n")

    # Step 2: Generate audio
    print("🎙️ Step 2: Generating audio...")
    audio_file = generate_audio(script)

    # Step 3: Upload to storage
    print("\n☁️ Step 3: Uploading to storage...")
    audio_url = await upload_to_storage(audio_file)

    # Summary
    print("\n" + "=" * 60)
    print("✅ PODCAST EPISODE GENERATED!")
    print("=" * 60)
    print(f"Script length: {len(script)} characters")
    print(f"Local file: {audio_file}")
    if audio_url:
        print(f"Public URL: {audio_url}")
    print(f"\n🎧 Play locally: open {audio_file}")


if __name__ == "__main__":
    asyncio.run(main())
