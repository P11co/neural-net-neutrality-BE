#!/usr/bin/env python3
"""
Seed test articles directly to InsForge via REST API
Usage: python3 seed-articles-api.py
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

INSFORGE_BASE_URL = os.getenv("INSFORGE_BASE_URL", "https://sv7kpi43.us-east.insforge.app")
INSFORGE_API_KEY = os.getenv("INSFORGE_API_KEY")

if not INSFORGE_API_KEY:
    print("❌ Error: INSFORGE_API_KEY not found in .env")
    exit(1)

headers = {
    "apikey": INSFORGE_API_KEY,
    "Authorization": f"Bearer {INSFORGE_API_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def create_tables():
    """Check if tables exist by trying to query them"""
    print("🔍 Checking if tables exist...")

    # Try to query news_sources
    try:
        response = requests.get(
            f"{INSFORGE_BASE_URL}/rest/v1/news_sources",
            headers=headers,
            params={"limit": 1}
        )
        if response.status_code == 200:
            print("✓ news_sources table exists")
        else:
            print(f"⚠️  news_sources table might not exist (status: {response.status_code})")
    except Exception as e:
        print(f"⚠️  Error checking news_sources: {e}")

    # Try to query news_articles
    try:
        response = requests.get(
            f"{INSFORGE_BASE_URL}/rest/v1/news_articles",
            headers=headers,
            params={"limit": 1}
        )
        if response.status_code == 200:
            print("✓ news_articles table exists")
        else:
            print(f"⚠️  news_articles table might not exist (status: {response.status_code})")
    except Exception as e:
        print(f"⚠️  Error checking news_articles: {e}")

def insert_news_sources():
    """Insert news sources"""
    print("\n📰 Inserting news sources...")

    sources = [
        {"name": "BBC", "url": "https://www.bbc.com"},
        {"name": "Reuters", "url": "https://www.reuters.com"},
        {"name": "Straight Arrow News", "url": "https://www.straightarrownews.com"}
    ]

    source_ids = {}

    for source in sources:
        try:
            # Try to insert
            response = requests.post(
                f"{INSFORGE_BASE_URL}/rest/v1/news_sources",
                headers=headers,
                json=source
            )

            if response.status_code in [200, 201]:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    source_id = result[0].get("id")
                else:
                    source_id = result.get("id")
                source_ids[source["name"]] = source_id
                print(f"✓ Inserted {source['name']} (id: {source_id})")
            elif response.status_code == 409:
                # Already exists, fetch the ID
                print(f"⚠️  {source['name']} already exists, fetching ID...")
                get_response = requests.get(
                    f"{INSFORGE_BASE_URL}/rest/v1/news_sources",
                    headers=headers,
                    params={"name": f"eq.{source['name']}", "select": "id"}
                )
                if get_response.status_code == 200:
                    results = get_response.json()
                    if results:
                        source_ids[source["name"]] = results[0]["id"]
                        print(f"✓ Found {source['name']} (id: {source_ids[source['name']]})")
            else:
                print(f"✗ Failed to insert {source['name']}: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error inserting {source['name']}: {e}")

    return source_ids

def insert_articles(source_ids):
    """Insert test articles"""
    print("\n📝 Inserting test articles...")

    now = datetime.now()

    articles = [
        {
            "title": "AI Regulation Bill Passes Senate Committee",
            "content": "The Senate Commerce Committee approved landmark legislation today that would establish federal oversight of artificial intelligence systems. The bipartisan bill, supported by both Democrats and Republicans, aims to create safety standards for AI models while promoting innovation. Proponents argue it provides necessary guardrails, while critics worry it may stifle technological progress. The bill now moves to the full Senate for consideration.",
            "url": "https://www.bbc.com/news/technology-ai-regulation-2025",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "source_id": source_ids.get("BBC")
        },
        {
            "title": "Federal Reserve Holds Interest Rates Steady",
            "content": "The Federal Reserve announced it will maintain current interest rates following its policy meeting, citing stable inflation and steady economic growth. Fed Chair Jerome Powell stated the central bank remains data-dependent and will adjust policy as needed. Markets responded positively to the decision, with major indices gaining ground. Economists predict rates will remain unchanged through the end of the year.",
            "url": "https://www.reuters.com/markets/fed-rates-2025",
            "published_at": (now - timedelta(hours=3)).isoformat(),
            "source_id": source_ids.get("Reuters")
        },
        {
            "title": "Bipartisan Infrastructure Projects Break Ground Nationwide",
            "content": "Construction began today on dozens of infrastructure projects across the country, funded by the 2021 bipartisan infrastructure law. Projects include bridge repairs, highway expansions, and broadband deployment in rural areas. Transportation Secretary Pete Buttigieg toured sites in three states, highlighting the economic benefits and job creation. Both parties claimed credit for the achievements during separate press conferences.",
            "url": "https://www.straightarrownews.com/politics/infrastructure-projects-2025",
            "published_at": (now - timedelta(hours=4)).isoformat(),
            "source_id": source_ids.get("Straight Arrow News")
        },
        {
            "title": "Tech Companies Announce Voluntary AI Safety Commitments",
            "content": "Major technology companies including Google, Microsoft, and OpenAI pledged new voluntary safety commitments for AI development. The agreements include increased transparency, third-party audits, and investment in AI safety research. The White House praised the commitments as a positive step, though some advocates argue binding regulations are still necessary. The announcements come amid growing calls for AI governance.",
            "url": "https://www.bbc.com/news/technology-ai-safety-2025",
            "published_at": (now - timedelta(hours=5)).isoformat(),
            "source_id": source_ids.get("BBC")
        },
        {
            "title": "Supreme Court Agrees to Hear Social Media Regulation Case",
            "content": "The U.S. Supreme Court will hear arguments on the constitutionality of state laws regulating social media platforms. The cases from Texas and Florida involve restrictions on content moderation practices. Tech industry groups argue the laws violate free speech rights, while state officials contend platforms have too much power. Legal experts call it one of the most significant First Amendment cases in decades.",
            "url": "https://www.reuters.com/legal/supreme-court-social-media-2025",
            "published_at": (now - timedelta(hours=6)).isoformat(),
            "source_id": source_ids.get("Reuters")
        }
    ]

    inserted_count = 0

    for article in articles:
        if not article["source_id"]:
            print(f"⚠️  Skipping article (no source_id): {article['title']}")
            continue

        try:
            response = requests.post(
                f"{INSFORGE_BASE_URL}/rest/v1/news_articles",
                headers=headers,
                json=article
            )

            if response.status_code in [200, 201]:
                inserted_count += 1
                print(f"✓ Inserted: {article['title'][:50]}...")
            elif response.status_code == 409:
                print(f"⚠️  Already exists: {article['title'][:50]}...")
            else:
                print(f"✗ Failed to insert article: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error inserting article: {e}")

    print(f"\n✅ Inserted {inserted_count} new articles")

def verify_articles():
    """Verify articles were inserted"""
    print("\n🔍 Verifying articles...")

    try:
        response = requests.get(
            f"{INSFORGE_BASE_URL}/rest/v1/news_articles",
            headers=headers,
            params={
                "select": "title,published_at,news_sources(name)",
                "order": "published_at.desc",
                "limit": 5
            }
        )

        if response.status_code == 200:
            articles = response.json()
            print(f"\n✅ Found {len(articles)} articles:")
            for i, article in enumerate(articles, 1):
                source = article.get("news_sources", {})
                source_name = source.get("name", "Unknown") if isinstance(source, dict) else "Unknown"
                print(f"  {i}. {article['title'][:60]}... ({source_name})")
        else:
            print(f"✗ Failed to verify: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ Error verifying: {e}")

def main():
    print("=" * 70)
    print("🌱 Seeding Test Articles to InsForge")
    print("=" * 70)

    create_tables()
    source_ids = insert_news_sources()

    if not source_ids:
        print("\n❌ Failed to create/fetch news sources")
        exit(1)

    insert_articles(source_ids)
    verify_articles()

    print("\n" + "=" * 70)
    print("✅ Seeding complete!")
    print("=" * 70)
    print("\nYou can now generate a podcast:")
    print("  curl -X POST http://localhost:8081/generate-podcast | python3 -m json.tool")

if __name__ == "__main__":
    main()
