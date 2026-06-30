"""
backend/discovery/orchestrator.py

Runs all 3 discovery methods AT THE SAME TIME.
Merges results. Sends every URL to the Universal Web Hunter.
"""
import logging
import asyncio
from backend.discovery.hashtag_crawl import hashtag_discovery
from backend.discovery.dorking import dork_search
from backend.discovery.bing_search import bing_search
from backend.discovery.reverse_image import reverse_image_search

# Ensure run_hunt is accessible
try:
    from backend.crawlers.worker import run_hunt_task
except ImportError:
    run_hunt_task = None

logger = logging.getLogger(__name__)

async def discover_and_hunt(asset: dict) -> dict:
    """
    Runs all discovery methods concurrently.
    Merges results. Sends every URL to the Universal Web Hunter.
    """
    title = asset.get("title", "")
    owner_domain = asset.get("owner_domain", "")
    storage_url = asset.get("storage_url", "")
    owner_id = asset.get("owner_id", "system")

    if not title:
        logger.warning("Asset has no title, discovery may be limited.")

    # Run primary methods
    tasks = [
        hashtag_discovery(title),
        dork_search(title, owner_domain),
        reverse_image_search(storage_url),
        bing_search(title)  # Run bing concurrently as fallback/extra
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    hashtag_urls = []
    dork_urls = []
    reverse_urls = []
    bing_urls = []

    if not isinstance(results[0], Exception):
        hashtag_urls = results[0]
    if not isinstance(results[1], Exception):
        dork_urls = results[1]
    if not isinstance(results[2], Exception):
        reverse_urls = results[2]
    if not isinstance(results[3], Exception):
        bing_urls = results[3]
    
    # Combine dork_urls and bing_urls
    dork_combined_urls = list(set(dork_urls + bing_urls))

    all_urls = list(set(hashtag_urls + dork_combined_urls + reverse_urls))

    if run_hunt_task:
        for url in all_urls:
            try:
                run_hunt_task.delay(
                    job_id=None,
                    seed_url=url,
                    owner_id=owner_id,
                    max_depth=1,
                    max_pages=5,
                )
            except Exception as e:
                logger.error("Failed to dispatch hunt task for %s: %s", url, e)
    else:
        logger.warning("Celery task run_hunt_task is not available. Skipping hunt dispatch.")

    return {
        "hashtag_found": len(hashtag_urls),
        "dorking_found": len(dork_combined_urls),
        "reverse_image_found": len(reverse_urls),
        "total_unique_urls": len(all_urls),
    }
