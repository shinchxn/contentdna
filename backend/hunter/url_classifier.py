"""
backend/hunter/url_classifier.py
Exactly as specified in the build spec.
"""
from enum import Enum


class URLType(Enum):
    YOUTUBE = "youtube"
    LIVE    = "live"
    SOCIAL  = "social"
    DIRECT  = "direct"
    STATIC  = "static"


YOUTUBE_DOMAINS = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com"]
LIVE_EXT        = [".m3u8", ".mpd"]
SOCIAL_DOMAINS  = [
    "instagram.com", "tiktok.com", "twitter.com", "x.com",
    "reddit.com", "pinterest.com", "flickr.com", "tumblr.com",
]
DIRECT_EXT      = [
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
]


def classify_url(url: str) -> URLType:
    u = url.lower()
    if any(d in u for d in YOUTUBE_DOMAINS):      return URLType.YOUTUBE
    if any(u.endswith(e) for e in LIVE_EXT):       return URLType.LIVE
    if "twitch.tv" in u or "youtube.com/live" in u: return URLType.LIVE
    if any(d in u for d in SOCIAL_DOMAINS):        return URLType.SOCIAL
    if any(u.split("?")[0].endswith(e) for e in DIRECT_EXT): return URLType.DIRECT
    return URLType.STATIC
