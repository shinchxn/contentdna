"""
backend/discovery/hashtag_crawl.py

Method 1: Hashtag Crawling (Weak Discovery)
Only catches careless reposts that happen to use similar tags.
Runs in background, low priority.
"""
import logging
import asyncio
from backend.crawlers.instagram import _get_instagram_client
from backend.config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

logger = logging.getLogger(__name__)

def generate_tags_from_title(title: str) -> list[str]:
    """Basic extraction of hashtags from a title."""
    words = [w.lower() for w in title.split() if w.isalnum() and len(w) > 3]
    tags = []
    if words:
        tags.append("".join(words)) # e.g. "sportshighlights"
    return tags

async def crawl_instagram_hashtags(tags: list[str]) -> list[str]:
    """Fetch recent posts for tags and extract media URLs."""
    urls = []
    try:
        if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
            logger.warning("Hashtag discovery (Instagram) disabled: missing credentials.")
            return urls
            
        cl = _get_instagram_client()
        for tag in tags:
            try:
                # Use synchronous call in executor if needed, but it's blocking here for simplicity.
                # In production we might want to wrap this in run_in_executor
                medias = cl.hashtag_medias_recent(tag, amount=5)
                for media in medias:
                    page_url = f"https://www.instagram.com/p/{media.code}/"
                    urls.append(page_url)
            except Exception as e:
                logger.debug("Instagram hashtag error #%s: %s", tag, e)
            await asyncio.sleep(1) # simple backoff
    except Exception as e:
         logger.warning("Instagram client error: %s", e)
    return urls

async def crawl_tiktok_hashtags(tags: list[str]) -> list[str]:
    """Fetch tiktok tags. We return the tag page URL to let the hunter handle it."""
    urls = []
    for tag in tags:
         urls.append(f"https://www.tiktok.com/tag/{tag}")
    return urls

async def hashtag_discovery(asset_title: str) -> list[str]:
    """
    Weak discovery method. Only catches careless reposts that
    happen to use similar tags. Runs in background, low priority.
    """
    tags = generate_tags_from_title(asset_title)
    urls = []
    urls += await crawl_instagram_hashtags(tags)
    urls += await crawl_tiktok_hashtags(tags)
    return list(set(urls))
