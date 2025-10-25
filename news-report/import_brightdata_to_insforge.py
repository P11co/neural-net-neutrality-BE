#!/usr/bin/env python3
"""
Import Bright Data scraped news JSON into InsForge database
Usage: python import_brightdata_to_insforge.py <json_file_path> <source_name>
Example: python import_brightdata_to_insforge.py data/bbc_news.json BBC
"""

import json
import sys
import os
from datetime import datetime
import requests

# InsForge configuration
INSFORGE_BASE_URL = "https://sv7kpi43.us-east.insforge.app"
INSFORGE_API_KEY = os.environ.get("INSFORGE_API_KEY", "ik_194453edb70ffcd51d76e2718b3f9eed")

# News source ID mapping (from your InsForge database)
SOURCE_IDS = {
    "BBC": "969e05ab-1549-4c61-a7ad-accff1f0eb5f",
    "Reuters": "6cf6e9c0-a4b4-41be-8071-c74b722101e8",
    "Straight Arrow News": "8bfc9d71-b0ec-43be-a899-818bad04a684"
}


def parse_brightdata_article(article, source_id):
    """
    Parse a Bright Data article object to InsForge schema

    Bright Data schema:
    - headline: article title
    - description: article summary/excerpt
    - article_image: featured image URL
    - section_name: category
    - related_articles: list of related articles (ignored for now)
    - content_type: "article"
    - input.url: source URL

    InsForge schema:
    - source_id: UUID
    - title: text
    - url: text (unique, required - extracted from related_articles or generated)
    - content: text (description in this case)
    - summary: text (first 200 chars of description)
    - author: text (not provided by Bright Data)
    - published_at: timestamp (not provided, use current time)
    - category: text (section_name)
    - image_url: text
    """

    # Extract URL from related_articles if this is a headline article
    # For now, we'll use the headline as a unique identifier
    # In production, you'd want actual article URLs
    url = article.get("input", {}).get("url", "")

    # Generate a pseudo-URL if not available (for uniqueness constraint)
    if not url or url == "https://www.bbc.com/":
        # Use headline hash for unique URL
        import hashlib
        headline_hash = hashlib.md5(article["headline"].encode()).hexdigest()[:12]
        base_domain = "https://www.bbc.com/news/articles/"
        url = f"{base_domain}{headline_hash}"

    return {
        "source_id": source_id,
        "title": article.get("headline", "").strip(),
        "url": url,
        "content": article.get("description", "").strip(),
        "summary": article.get("description", "")[:200].strip() + "..." if len(article.get("description", "")) > 200 else article.get("description", "").strip(),
        "author": None,  # Not provided by Bright Data
        "published_at": datetime.now().isoformat(),  # Not provided, use current time
        "category": article.get("section_name", "general").strip(),
        "image_url": article.get("article_image", "").strip() or None
    }


def insert_articles_to_insforge(articles):
    """
    Bulk insert articles into InsForge database
    Uses the InsForge REST API
    """

    headers = {
        "Content-Type": "application/json",
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}"
    }

    # InsForge uses PostgREST, so we can insert multiple records
    url = f"{INSFORGE_BASE_URL}/rest/v1/news_articles"

    inserted = 0
    skipped = 0
    errors = []

    for article in articles:
        try:
            response = requests.post(
                url,
                headers=headers,
                json=article,
                params={"on_conflict": "url"}  # Skip duplicates
            )

            if response.status_code in [200, 201]:
                inserted += 1
                print(f"✓ Inserted: {article['title'][:60]}...")
            elif response.status_code == 409:
                skipped += 1
                print(f"⊘ Skipped (duplicate): {article['title'][:60]}...")
            else:
                errors.append(f"Error inserting '{article['title'][:40]}': {response.status_code} - {response.text}")
                print(f"✗ Error: {response.status_code} - {article['title'][:60]}...")
        except Exception as e:
            errors.append(f"Exception for '{article['title'][:40]}': {str(e)}")
            print(f"✗ Exception: {article['title'][:60]}... - {str(e)}")

    return inserted, skipped, errors


def update_source_last_scraped(source_id):
    """Update the last_scraped_at timestamp for a news source"""

    headers = {
        "Content-Type": "application/json",
        "apikey": INSFORGE_API_KEY,
        "Authorization": f"Bearer {INSFORGE_API_KEY}",
        "Prefer": "return=minimal"
    }

    url = f"{INSFORGE_BASE_URL}/rest/v1/news_sources"

    try:
        response = requests.patch(
            url,
            headers=headers,
            json={"last_scraped_at": datetime.now().isoformat()},
            params={"id": f"eq.{source_id}"}
        )

        if response.status_code in [200, 204]:
            print(f"✓ Updated last_scraped_at for source")
        else:
            print(f"⚠ Failed to update last_scraped_at: {response.status_code}")
    except Exception as e:
        print(f"⚠ Exception updating last_scraped_at: {str(e)}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python import_brightdata_to_insforge.py <json_file_path> <source_name>")
        print("Example: python import_brightdata_to_insforge.py data/bbc_news.json BBC")
        print(f"\nAvailable sources: {', '.join(SOURCE_IDS.keys())}")
        sys.exit(1)

    json_file = sys.argv[1]
    source_name = sys.argv[2]

    # Validate source
    if source_name not in SOURCE_IDS:
        print(f"Error: Unknown source '{source_name}'")
        print(f"Available sources: {', '.join(SOURCE_IDS.keys())}")
        sys.exit(1)

    source_id = SOURCE_IDS[source_name]

    # Load JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            brightdata_articles = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{json_file}': {str(e)}")
        sys.exit(1)

    print(f"\n📰 Importing {len(brightdata_articles)} articles from {source_name}...")
    print(f"Source ID: {source_id}\n")

    # Parse articles
    parsed_articles = []
    for article in brightdata_articles:
        if article.get("content_type") == "article" and article.get("headline"):
            parsed = parse_brightdata_article(article, source_id)
            parsed_articles.append(parsed)

    print(f"Parsed {len(parsed_articles)} valid articles\n")

    # Insert into InsForge
    inserted, skipped, errors = insert_articles_to_insforge(parsed_articles)

    # Update source timestamp
    if inserted > 0:
        update_source_last_scraped(source_id)

    # Summary
    print("\n" + "="*60)
    print(f"✓ Inserted: {inserted}")
    print(f"⊘ Skipped (duplicates): {skipped}")
    print(f"✗ Errors: {len(errors)}")
    print("="*60)

    if errors:
        print("\nErrors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")


if __name__ == "__main__":
    main()
