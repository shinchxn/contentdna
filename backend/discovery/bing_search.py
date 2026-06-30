"""
backend/discovery/bing_search.py

Method 2 Fallback: Bing Search
"""
import logging
import httpx
from backend.config import BING_SEARCH_API_KEY

logger = logging.getLogger(__name__)

async def bing_search(query: str) -> list[str]:
    if not BING_SEARCH_API_KEY:
        logger.warning("Bing search disabled: missing BING_SEARCH_API_KEY.")
        return []

    urls = []
    try:
        headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
        params = {"q": query, "count": 20}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers=headers, params=params
            )
            r.raise_for_status()
            data = r.json()
            urls = [item["url"] for item in data.get("webPages", {}).get("value", [])]
    except Exception as e:
        logger.error("Bing search error: %s", e)
    return urls
