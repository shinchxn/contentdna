"""
backend/crawlers/instagram.py

Instagram crawler using instagrapi.
Scans public hashtags related to sports content.
Extracts image and video URLs from each post.
Rate-limited to 3 seconds per media item.
Session is persisted to disk to avoid repeated logins.
"""
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

SESSION_FILE = "./data/instagram_session.json"

DEFAULT_HASHTAGS = [
    "sportshighlights",
    "matchday",
    "football",
    "soccer",
    "cricketlive",
    "nba",
    "formula1",
    "tennislive",
]


def _get_instagram_client():
    """
    Create and return an authenticated instagrapi Client.
    Loads existing session from disk to avoid triggering login flows.
    """
    try:
        from instagrapi import Client
    except ImportError:
        raise RuntimeError(
            "instagrapi not installed. Run: pip install instagrapi"
        )

    from backend.config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise ValueError("Instagram credentials not set in .env")

    cl = Client()
    cl.delay_range = [2, 5]  # built-in rate limiting

    import os
    try:
        if os.path.exists(SESSION_FILE):
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        else:
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            cl.dump_settings(SESSION_FILE)
    except Exception as e:
        logger.warning("Instagram session error, retrying fresh login: %s", e)
        cl = Client()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.dump_settings(SESSION_FILE)

    return cl


async def crawl_instagram(hashtags: list[str] = None, posts_per_tag: int = 20):
    """
    For each hashtag, fetch recent posts.
    Extract media URLs and run detection on each.
    3-second rate limit between requests.
    """
    try:
        from backend.detection.engine import detect_from_url
    except ImportError as e:
        logger.error("Detection engine import failed: %s", e)
        return

    try:
        cl = _get_instagram_client()
    except (RuntimeError, ValueError) as e:
        logger.warning("Instagram crawler disabled: %s", e)
        return

    if hashtags is None:
        hashtags = DEFAULT_HASHTAGS

    total_found = 0
    total_matched = 0

    for tag in hashtags:
        try:
            medias = cl.hashtag_medias_recent(tag, amount=posts_per_tag)
        except Exception as e:
            logger.warning("Instagram hashtag error #%s: %s", tag, e)
            await asyncio.sleep(5)  # back off on error
            continue

        for media in medias:
            media_url = None
            try:
                if media.media_type == 1:   # Photo
                    media_url = str(media.thumbnail_url or media.thumbnail_url)
                elif media.media_type == 2:  # Video
                    media_url = str(media.video_url)
                elif media.media_type == 8:  # Album — take first item
                    if media.resources:
                        first = media.resources[0]
                        media_url = str(first.thumbnail_url or first.video_url or "")
            except Exception as e:
                logger.debug("Media URL extraction error: %s", e)
                continue

            if not media_url:
                continue

            page_url = f"https://www.instagram.com/p/{media.code}/"
            total_found += 1

            try:
                result = await detect_from_url(
                    url=media_url,
                    platform="instagram",
                    page_url=page_url,
                    source_type="crawler",
                )
                if result and result.matched:
                    total_matched += 1
            except Exception as e:
                logger.debug("Detection error for %s: %s", media_url, e)

            time.sleep(3)  # Instagram rate limit: 3 seconds between requests

    logger.info(
        "[Instagram] Crawl complete — %d media found, %d matches",
        total_found, total_matched,
    )
    return {"found": total_found, "matched": total_matched}


async def check_instagram_account(handle: str, owner_id: str, limit: int = 20) -> dict:
    """
    Fetch a specific Instagram account's recent media and run detection.
    """
    from backend.detection.engine import detect_from_url

    limit = min(limit, 50)  # server-side cap

    try:
        cl = _get_instagram_client()
    except (RuntimeError, ValueError) as e:
        return {"error": str(e), "found": 0, "matched": 0}

    found = matched = 0
    try:
        user_id = cl.user_id_from_username(handle)
        medias = cl.user_medias(user_id, amount=limit)
        for media in medias:
            media_url = None
            if media.media_type == 1:
                media_url = str(media.thumbnail_url or media.thumbnail_url)
            elif media.media_type == 2:
                media_url = str(media.video_url)
            elif media.media_type == 8 and media.resources:
                first = media.resources[0]
                media_url = str(first.thumbnail_url or first.video_url or "")
            if not media_url:
                continue
            
            found += 1
            try:
                result = await detect_from_url(
                    url=media_url, platform="instagram",
                    page_url=f"https://www.instagram.com/p/{media.code}/",
                    source_type="manual_account_check",
                )
                if result.matched:
                    matched += 1
            except Exception as e:
                logger.debug("Detection error for %s: %s", media_url, e)
            await asyncio.sleep(1)  # lighter rate limit than full sweep
    except Exception as e:
        return {"error": str(e), "found": found, "matched": matched}

    return {"found": found, "matched": matched}
