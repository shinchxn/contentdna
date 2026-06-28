"""
backend/hunter/url_classifier.py
──────────────────────────────────
Classifies any URL into one of five types so the hunt_job can route it
to the correct extractor with zero per-site branching logic.
"""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


# ── Domain / extension tables ─────────────────────────────────────────────────

YOUTUBE_DOMAINS = [
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "twitch.tv",                         # VODs → yt-dlp handles them too
]

LIVE_DOMAINS = ["twitch.tv"]
LIVE_PATH_KEYWORDS = ["/live", "/stream", "livestream"]
LIVE_EXTENSIONS = [".m3u8", ".mpd"]

SOCIAL_DOMAINS = [
    "instagram.com", "tiktok.com", "twitter.com", "x.com",
    "reddit.com", "pinterest.com", "flickr.com", "tumblr.com",
    "deviantart.com", "pixiv.net", "artstation.com", "500px.com",
    "facebook.com", "fb.com",
]

DIRECT_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv",
]


class URLType(Enum):
    YOUTUBE = "youtube"     # → yt-dlp extractor
    LIVE    = "live"        # → streamlink extractor
    SOCIAL  = "social"      # → gallery-dl extractor
    DIRECT  = "direct"      # → direct_extractor (httpx GET)
    STATIC  = "static"      # → scrapy + playwright fallback


def classify_url(url: str) -> URLType:
    """
    Classify *url* into a URLType enum value.

    Rules (evaluated in priority order):
        1. LIVE   — .m3u8/.mpd extension  OR  twitch.tv  OR  youtube.com/live
        2. YOUTUBE — youtube.com / youtu.be / vimeo / dailymotion
        3. SOCIAL — known social platform domains
        4. DIRECT — URL path ends with a media file extension
        5. STATIC — everything else (generic web page)
    """
    url_lower = url.lower()

    # ── 1. Live streams ──────────────────────────────────────────────────────
    if any(url_lower.endswith(ext) for ext in LIVE_EXTENSIONS):
        return URLType.LIVE
    if "twitch.tv" in url_lower:
        return URLType.LIVE
    if "youtube.com/live" in url_lower:
        return URLType.LIVE

    # ── 2. YouTube-style VOD platforms ───────────────────────────────────────
    if any(d in url_lower for d in YOUTUBE_DOMAINS):
        return URLType.YOUTUBE

    # ── 3. Social media platforms ─────────────────────────────────────────────
    if any(d in url_lower for d in SOCIAL_DOMAINS):
        return URLType.SOCIAL

    # ── 4. Direct media URL ───────────────────────────────────────────────────
    parsed_path = urlparse(url).path.lower()
    if any(parsed_path.endswith(ext) for ext in DIRECT_EXTENSIONS):
        return URLType.DIRECT

    # ── 5. Generic static/dynamic web page ───────────────────────────────────
    return URLType.STATIC
