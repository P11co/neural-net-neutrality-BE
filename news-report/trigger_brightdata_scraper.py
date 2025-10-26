#!/usr/bin/env python3
"""
Trigger Bright Data scraper via API and download results
Usage: python trigger_brightdata_scraper.py
"""

import os
import requests
import time
import json
from datetime import datetime

# Bright Data Configuration
BRIGHTDATA_API_TOKEN = os.environ.get("BRIGHTDATA_API_TOKEN", "")  # Set your token
COLLECTOR_ID = "c_mh63scdem3jiaigq0"  # From your screenshot
BRIGHTDATA_API_BASE = "https://api.brightdata.com/dca"

# News sources to scrape
SOURCES = {
    "BBC": "https://www.bbc.com/",
    # "Reuters": "https://www.reuters.com/",
    # "Straight Arrow News": "https://www.straightarrownews.com/"
}


def trigger_scraper(url, collector_id=COLLECTOR_ID):
    """
    Trigger a Bright Data scraper job for a given URL using trigger_immediate

    Args:
        url: The URL to scrape
        collector_id: Your Bright Data collector ID

    Returns:
        snapshot_id: The ID of the created scraping job
    """

    # API endpoint to trigger immediate collection
    endpoint = f"{BRIGHTDATA_API_BASE}/trigger_immediate"

    # Request payload - simple URL object
    payload = {"url": url}

    # Headers
    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Query parameter
    params = {
        "collector": collector_id
    }

    try:
        print(f"🚀 Triggering immediate scraper for: {url}")
        response = requests.post(
            endpoint,
            headers=headers,
            params=params,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        # Check for snapshot_id or response_id
        snapshot_id = result.get("snapshot_id")
        response_id = result.get("response_id")

        if snapshot_id:
            print(f"✓ Job created with snapshot_id: {snapshot_id}")
            return snapshot_id
        elif response_id:
            print(f"✓ Job created with response_id: {response_id}")
            print(f"📖 Documentation: {result.get('how_to_use', 'N/A')}")
            return response_id
        else:
            print(f"⚠️  Warning: No snapshot_id or response_id returned. Response: {result}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Error triggering scraper: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return None


def check_job_status(snapshot_id):
    """
    Check the status of a Bright Data scraping job

    Args:
        snapshot_id: The snapshot ID returned from trigger_scraper

    Returns:
        dict with status information
    """

    endpoint = f"{BRIGHTDATA_API_BASE}/snapshot/{snapshot_id}"

    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}"
    }

    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"✗ Error checking status: {e}")
        return None


def download_results(snapshot_id, output_file=None):
    """
    Download the results of a completed scraping job

    Args:
        snapshot_id: The snapshot ID of the completed job
        output_file: Optional file path to save results (default: auto-generated)

    Returns:
        Path to downloaded file or None
    """

    endpoint = f"{BRIGHTDATA_API_BASE}/snapshot/{snapshot_id}"

    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}"
    }

    # Query parameter to get the actual data
    params = {
        "format": "json"
    }

    try:
        print(f"📥 Downloading results for snapshot: {snapshot_id}")
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        # Generate output filename if not provided
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/brightdata_{snapshot_id}_{timestamp}.json"

        # Ensure data directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ Results saved to: {output_file}")
        return output_file

    except requests.exceptions.RequestException as e:
        print(f"✗ Error downloading results: {e}")
        return None


def wait_for_completion(snapshot_id, max_wait_seconds=300, check_interval=10):
    """
    Poll the API until the job is complete or timeout

    Args:
        snapshot_id: The snapshot ID to monitor
        max_wait_seconds: Maximum time to wait (default: 5 minutes)
        check_interval: Seconds between status checks (default: 10 seconds)

    Returns:
        True if completed successfully, False otherwise
    """

    print(f"⏳ Waiting for job {snapshot_id} to complete...")

    elapsed = 0
    while elapsed < max_wait_seconds:
        status_info = check_job_status(snapshot_id)

        if status_info is None:
            print(f"⚠ Could not check status")
            return False

        status = status_info.get("status")
        progress = status_info.get("progress", {})
        discovered = progress.get("discovered", 0)
        collected = progress.get("collected", 0)

        print(f"Status: {status} | Discovered: {discovered} | Collected: {collected}")

        if status == "ready":
            print(f"✓ Job completed successfully!")
            return True
        elif status in ["failed", "cancelled"]:
            print(f"✗ Job {status}")
            return False

        time.sleep(check_interval)
        elapsed += check_interval

    print(f"⏱ Timeout waiting for job to complete")
    return False


def scrape_news_source(source_name, source_url):
    """
    Complete workflow: trigger scraper, wait for completion, download results

    Args:
        source_name: Name of the news source (e.g., "BBC")
        source_url: URL to scrape

    Returns:
        Path to downloaded file or None
    """

    print(f"\n{'='*60}")
    print(f"Scraping {source_name}")
    print(f"{'='*60}")

    # Step 1: Trigger the scraper
    snapshot_id = trigger_scraper(source_url)

    if snapshot_id is None:
        print(f"Failed to trigger scraper for {source_name}")
        return None

    # Step 2: Wait for completion
    success = wait_for_completion(snapshot_id, max_wait_seconds=300)

    if not success:
        print(f"Scraping job did not complete successfully for {source_name}")
        return None

    # Step 3: Download results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/{source_name.lower().replace(' ', '_')}_{timestamp}.json"

    result_file = download_results(snapshot_id, output_file)

    return result_file


def main():
    """
    Main function to scrape all configured news sources
    """

    # Check for API token
    if not BRIGHTDATA_API_TOKEN:
        print("❌ Error: BRIGHTDATA_API_TOKEN environment variable not set")
        print("Please set it with: export BRIGHTDATA_API_TOKEN='your_token_here'")
        return

    print("🌐 Starting Bright Data News Scraper")
    print(f"Collector ID: {COLLECTOR_ID}")
    print(f"Sources to scrape: {len(SOURCES)}\n")

    results = {}

    for source_name, source_url in SOURCES.items():
        result_file = scrape_news_source(source_name, source_url)
        results[source_name] = result_file

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for source_name, result_file in results.items():
        if result_file:
            print(f"✓ {source_name}: {result_file}")
        else:
            print(f"✗ {source_name}: Failed")

    print(f"\n{'='*60}")
    print("Next steps:")
    print("1. Run the import script to load data into InsForge:")
    for source_name, result_file in results.items():
        if result_file:
            print(f"   node import_brightdata_to_insforge.js {result_file} \"{source_name}\"")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
