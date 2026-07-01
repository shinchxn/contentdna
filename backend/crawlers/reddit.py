"""
backend/crawlers/reddit.py

Reddit crawler using PRAW (official Reddit API).
Scans 9 target sports subreddits for image/video posts.
Every media URL is fed into the shared detection engine.
"""
import logging
import asyncio

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "sports", "soccer", "nba", "nfl", "cricket",
    "formula1", "tennis", "highlights", "sportsnews",
]
POSTS_PER_SUB = 25


def _get_reddit_client():
    """Build a read-only PRAW Reddit client from config."""
    try:
        import praw
        from backend.config import (
            REDDIT_CLIENT_ID,
            REDDIT_CLIENT_SECRET,
            REDDIT_USER_AGENT,
        )
        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
            raise ValueError("Reddit credentials not set in .env")
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT or "contentdna/1.0",
            read_only=True,
        )
    except ImportError:
        raise RuntimeError("praw is not installed. Run: pip install praw")


def _extract_media_from_post(post) -> list[str]:
    """Return all image/video URLs from a Reddit post."""
    urls = []
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    VIDEO_EXTS = {".mp4", ".gifv", ".mov"}

    url = getattr(post, "url", "") or ""
    suffix = url.split("?")[0].lower()
    if any(suffix.endswith(ext) for ext in IMAGE_EXTS | VIDEO_EXTS):
        urls.append(url)

    # Gallery posts
    metadata = getattr(post, "media_metadata", None) or {}
    for item in metadata.values():
        if isinstance(item, dict) and item.get("e") == "Image":
            img_url = item.get("s", {}).get("u", "")
            if img_url:
                urls.append(img_url.replace("&amp;", "&"))

    # Native Reddit video
    media = getattr(post, "media", None) or {}
    if isinstance(media, dict) and "reddit_video" in media:
        fallback = media["reddit_video"].get("fallback_url", "")
        if fallback:
            urls.append(fallback)

    return list(dict.fromkeys(urls))  # deduplicate while preserving order


async def crawl_reddit(owner_id: str = None):
    """
    Main entry point: scan each subreddit for new posts,
    extract media URLs, run detection on each one.
    """
    try:
        from backend.detection.engine import detect_from_url
    except ImportError as e:
        logger.error("Detection engine import failed: %s", e)
        return

    try:
        reddit = _get_reddit_client()
    except (RuntimeError, ValueError) as e:
        logger.warning("Reddit crawler disabled: %s", e)
        return

    total_found = 0
    total_matched = 0

    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.new(limit=POSTS_PER_SUB):
                media_urls = _extract_media_from_post(post)
                for url in media_urls:
                    total_found += 1
                    try:
                        result = await detect_from_url(
                            url=url,
                            platform="reddit",
                            page_url=f"https://reddit.com{post.permalink}",
                            source_type="crawler",
                        )
                        if result and result.matched:
                            total_matched += 1
                    except Exception as e:
                        logger.debug("Detection error for %s: %s", url, e)
                    await asyncio.sleep(0.1)  # be a good citizen
        except Exception as e:
            logger.warning("Failed to crawl r/%s: %s", sub_name, e)

    logger.info(
        "[Reddit] Crawl complete — %d media found, %d matches",
        total_found, total_matched,
    )
    return {"found": total_found, "matched": total_matched}


async def check_reddit_account(handle: str, owner_id: str, limit: int = 25) -> dict:
    """
    Fetch a specific redditor's recent submissions and run detection on each.

    Parameters
    ----------
    handle   : Reddit username (without u/ prefix)
    owner_id : UUID of the owner requesting the check
    limit    : Max number of submissions to scan (server-side cap: 50)

    Returns
    -------
    dict with keys: found, matched — or an extra 'error' key on failure.
    """
    from backend.detection.engine import detect_from_url

    limit = min(limit, 50)  # server-side cap

    try:
        reddit = _get_reddit_client()
    except (RuntimeError, ValueError) as e:
        return {"error": str(e), "found": 0, "matched": 0}

    found = matched = 0
    try:
        redditor = reddit.redditor(handle)
        for post in redditor.submissions.new(limit=limit):
            for url in _extract_media_from_post(post):
                found += 1
                try:
                    result = await detect_from_url(
                        url=url,
                        platform="reddit",
                        page_url=f"https://reddit.com{post.permalink}",
                        source_type="manual_account_check",
                    )
                    if result.matched:
                        matched += 1
                except Exception as e:
                    logger.debug("Detection error for %s: %s", url, e)
    except Exception as e:
        return {"error": str(e), "found": found, "matched": matched}

    return {"found": found, "matched": matched}
