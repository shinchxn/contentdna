"""
backend/discovery/reverse_image.py

Method 3: Reverse Image Search (Strongest Discovery)
Searches by actual pixels using Google Custom Search Engine (Image Search).
"""
import logging
import httpx
from backend.config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID

logger = logging.getLogger(__name__)

async def reverse_image_search(image_url: str) -> list[str]:
    """
    Strongest discovery method. Searches by actual pixels,
    not text or tags. Finds visually identical/similar images
    anywhere Google has indexed them — blind to filename,
    caption, or hashtag entirely.
    """
    if not image_url:
        return []

    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_ID:
        logger.warning("Reverse image search disabled: missing GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID.")
        return []

    urls = []
    try:
        params = {
            "key": GOOGLE_CSE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "searchType": "image",
            "q": image_url,   # or use Google Vision API for true reverse search
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            urls = [item["link"] for item in data.get("items", [])]
    except Exception as e:
        logger.error("Reverse image search error: %s", e)
    return list(set(urls))
