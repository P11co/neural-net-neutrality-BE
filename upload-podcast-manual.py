#!/usr/bin/env python3
"""
Upload the generated podcast to InsForge and save to database
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

INSFORGE_BASE_URL = os.getenv("INSFORGE_BASE_URL", "https://sv7kpi43.us-east.insforge.app")
INSFORGE_API_KEY = os.getenv("INSFORGE_API_KEY")

# Path to generated podcast
podcast_file = "/Users/peter/Documents/berkeley/calhacks12/Neural-Net-Neutrality-BE/news-report/audio-data/podcast_20251026_011221.mp3"

# Read the script from test
script = """**[INTRO MUSIC FADES OUT]**

**Anchor:** Good evening, and welcome to tonight's news update. I'm your host, and we have an exciting lineup of stories that highlight the latest advancements in technology and space exploration. Let's dive right in.

**[TRANSITION SOUND EFFECT]**

**Anchor:** First up, Apple has just unveiled a revolutionary new chip architecture that could change the landscape of artificial intelligence. The M4 Neural chip boasts a dedicated neural engine with an impressive 40 cores, delivering an astounding processing power of over 35 trillion operations per second. This leap in on-device AI processing means users can expect features like real-time language translation, advanced image processing, and sophisticated machine learning—all without relying on cloud services. Industry experts are already predicting that this innovation could set a new standard for AI-powered consumer devices.

**[TRANSITION SOUND EFFECT]**

**Anchor:** Moving to the realm of quantum computing, researchers at MIT have achieved a significant milestone by successfully creating a stable 1000-qubit quantum processor. This breakthrough allows the processor to maintain quantum coherence for over 10 minutes, far exceeding previous records. Such advancements bring us closer to practical quantum computers capable of tackling complex problems in areas like drug discovery, climate modeling, and cryptography—challenges that are currently beyond the reach of classical computers.

**[TRANSITION SOUND EFFECT]**

**Anchor:** In a historic moment for humanity, SpaceX's Starship has successfully landed the first crewed mission on Mars. After a seven-month journey, the six-person crew touched down in Jezero Crater this morning at 6:47 AM EST. Commander Sarah Chen reported that all systems are nominal and the crew is in excellent health. This mission marks a monumental step in establishing a human presence on another planet, with plans underway to create a permanent research base over the next two years. NASA Administrator hailed this achievement as the most significant space milestone since the Apollo moon landing.

**[TRANSITION SOUND EFFECT]**

**Anchor:** On the cybersecurity front, researchers have uncovered a critical zero-day vulnerability affecting major cloud computing platforms, including AWS, Azure, and Google Cloud. Dubbed 'CloudBleed,' this flaw could potentially allow attackers to access sensitive data across shared infrastructure. In response, all three companies have released emergency patches and are actively collaborating with their customers to ensure system security. Experts are urging immediate updates and comprehensive security audits to mitigate any risks.

**[TRANSITION SOUND EFFECT]**

**Anchor:** Finally, in the field of medical technology, a new AI language model developed by researchers at Johns Hopkins has made waves by achieving a remarkable 94% score on the United States Medical Licensing Examination. This score surpasses the average human physician score of 87%, showcasing the model's sophisticated medical reasoning capabilities. While it's not intended to replace doctors, this technology holds promise for enhancing healthcare accessibility and supporting medical education. Clinical trials are set to begin next quarter to further explore its potential.

**[OUTRO MUSIC BEGINS]**

**Anchor:** That wraps up our news update for tonight. Thank you for joining us, and stay tuned for more stories that shape our world. Have a great evening!

**[OUTRO MUSIC FADES OUT]**"""

def upload_to_storage():
    """Upload MP3 to InsForge storage"""
    print("=" * 70)
    print("📤 Uploading podcast to InsForge Storage")
    print("=" * 70)

    headers = {
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
    }

    # Generate filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"daily-brief-{timestamp}.mp3"

    # Upload file
    with open(podcast_file, "rb") as f:
        files = {"file": (filename, f, "audio/mpeg")}

        response = requests.post(
            f"{INSFORGE_BASE_URL}/storage/v1/object/podcast-episodes/{filename}",
            headers=headers,
            files=files,
            timeout=120
        )

        print(f"Upload status: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code in [200, 201]:
            # Get public URL
            public_url = f"{INSFORGE_BASE_URL}/storage/v1/object/public/podcast-episodes/{filename}"
            print(f"✅ Upload successful!")
            print(f"🔗 Audio URL: {public_url}")
            return public_url, filename
        else:
            print(f"❌ Upload failed: {response.text}")
            return None, None

def save_to_database(audio_url):
    """Save episode to database via InsForge MCP"""
    print("\n" + "=" * 70)
    print("💾 Saving episode to database")
    print("=" * 70)

    today = datetime.now().date().isoformat()
    title = f"Daily Brief - {datetime.now().strftime('%B %d, %Y')}"

    # Since we can't use REST API, we'll use the consult MCP tool
    # For now, just return the data that should be inserted
    episode_data = {
        "title": title,
        "description": f"Your daily AI-generated neutral news podcast for {today}",
        "publication_date": today,
        "audio_url": audio_url,
        "duration_seconds": 249,  # ~4 minutes
        "script": script,
        "article_ids": []
    }

    print(f"Episode data prepared:")
    print(f"  Title: {episode_data['title']}")
    print(f"  Date: {episode_data['publication_date']}")
    print(f"  Audio URL: {episode_data['audio_url']}")
    print(f"  Duration: {episode_data['duration_seconds']}s")

    return episode_data

if __name__ == "__main__":
    print("\n🎙️ Manual Podcast Upload Tool\n")

    # Check if file exists
    if not os.path.exists(podcast_file):
        print(f"❌ Podcast file not found: {podcast_file}")
        exit(1)

    file_size = os.path.getsize(podcast_file) / (1024 * 1024)
    print(f"📁 Found podcast file: {file_size:.2f} MB\n")

    # Upload to storage
    audio_url, filename = upload_to_storage()

    if audio_url:
        # Prepare database entry
        episode_data = save_to_database(audio_url)

        print("\n" + "=" * 70)
        print("✅ UPLOAD COMPLETE!")
        print("=" * 70)
        print(f"\n📋 Next step: Insert this into podcast_episodes table:")
        print(f"\nINSERT INTO podcast_episodes (title, description, publication_date, audio_url, duration_seconds, script)")
        print(f"VALUES (")
        print(f"  '{episode_data['title']}',")
        print(f"  '{episode_data['description']}',")
        print(f"  '{episode_data['publication_date']}',")
        print(f"  '{episode_data['audio_url']}',")
        print(f"  {episode_data['duration_seconds']},")
        print(f"  '{script[:50]}...'")
        print(f");")
        print("\n" + "=" * 70)
    else:
        print("\n❌ Upload failed")
        exit(1)
