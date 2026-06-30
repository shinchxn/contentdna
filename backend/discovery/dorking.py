"""
backend/discovery/dorking.py

Method 2: Dorking (Strong Discovery)
Searches Google's index by title using specific dorks.
Finds reposts regardless of hashtags used.
"""
import logging
import time

logger = logging.getLogger(__name__)

DORK_TEMPLATES = [
    'site:instagram.com "{title}"',
    'site:tiktok.com "{title}"',
    'site:youtube.com "{title}" -{owner_domain}',
    'inurl:sports "{title}" -{owner_domain}',
    '"{title}" filetype:mp4 -{owner_domain}',
    '"{title}" filetype:jpg -{owner_domain}',
    '"{title}" site:reddit.com',
    'inurl:highlights "{title}" -{owner_domain}',
    '"{title}" "watch" -{owner_domain}',
    '"{title}" "download" filetype:mp4',
    '"{title}" {year} -{owner_domain}',
    'related:{owner_domain} "{title}"',
]

async def dork_search(title: str, owner_domain: str = "", year: str = "2026") -> list[str]:
    """
    Real discovery. Searches Google's own index by title —
    finds reposts regardless of hashtags used.
    """
    try:
        from googlesearch import search
    except ImportError:
        logger.error("googlesearch-python not installed. Run: pip install googlesearch-python")
        return []

    urls = []
    for template in DORK_TEMPLATES:
        query = template.format(title=title, owner_domain=owner_domain, year=year)
        try:
            # We run this synchronously inside the async function.
            # In a heavy production setting, run_in_executor would be better.
            for url in search(query, num_results=10):
                urls.append(url)
        except Exception as e:
             logger.debug("Dork search error for query '%s': %s", query, e)
        time.sleep(1)  # avoid rate limit (reduced from 10s for speed, but adjust as needed)
    return list(set(urls))
