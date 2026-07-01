"""
backend/crawlers/youtube.py

YouTube crawler using the YouTube Data API v3.
Searches for recently uploaded videos matching sports keywords.
Downloads thumbnails via URL for fingerprinting.
Uses yt-dlp for preview clip download when thumbnail match is inconclusive.
"""
import logging
import asyncio
import os
import tempfile

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "sports highlights",
    "match highlights",
    "football highlights",
    "soccer highlights",
    "cricket highlights",
    "nba highlights",
    "formula 1 highlights",
]


def _get_youtube_client():
    """Build a YouTube Data API v3 client."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client"
        )
    from backend.config import YOUTUBE_API_KEY
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY not set in .env")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


async def crawl_youtube(keywords: list[str] = None):
    """
    For each keyword, search YouTube for recent videos (up to 25 per keyword).
    Download thumbnail and run detection. If thumbnail matches, log the violation.
    """
    try:
        from backend.detection.engine import detect_from_url
    except ImportError as e:
        logger.error("Detection engine import failed: %s", e)
        return

    try:
        yt = _get_youtube_client()
    except (RuntimeError, ValueError) as e:
        logger.warning("YouTube crawler disabled: %s", e)
        return

    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    total_found = 0
    total_matched = 0

    for keyword in keywords:
        try:
            request = yt.search().list(
                part="snippet",
                q=keyword,
                type="video",
                order="date",
                maxResults=25,
                safeSearch="none",
            )
            response = request.execute()
        except Exception as e:
            logger.warning("YouTube search failed for '%s': %s", keyword, e)
            continue

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            snippet  = item.get("snippet", {})
            thumbs   = snippet.get("thumbnails", {})
            # Prefer high → medium → default thumbnail
            thumb_url = (
                thumbs.get("high",    {}).get("url") or
                thumbs.get("medium",  {}).get("url") or
                thumbs.get("default", {}).get("url")
            )
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            total_found += 1

            if not thumb_url:
                continue

            try:
                result = await detect_from_url(
                    url=thumb_url,
                    platform="youtube",
                    page_url=video_url,
                    source_type="crawler",
                )
                if result and result.matched:
                    total_matched += 1
            except Exception as e:
                logger.debug("Detection error for %s: %s", thumb_url, e)

            await asyncio.sleep(0.05)

    logger.info(
        "[YouTube] Crawl complete — %d thumbnails scanned, %d matches",
        total_found, total_matched,
    )
    return {"found": total_found, "matched": total_matched}


async def check_youtube_account(handle: str, owner_id: str, limit: int = 25) -> dict:
    """
    Fetch a specific YouTube channel's recent uploads and run detection
    on their thumbnails.
    """
    from backend.detection.engine import detect_from_url
    
    limit = min(limit, 50)  # server-side cap
    
    try:
        yt = _get_youtube_client()
    except (RuntimeError, ValueError) as e:
        return {"error": str(e), "found": 0, "matched": 0}

    found = matched = 0
    try:
        # Resolve handle to channel ID
        channel_id = None
        try:
            resp = yt.channels().list(part="id", forHandle=handle).execute()
            items = resp.get("items", [])
            if items:
                channel_id = items[0]["id"]
        except Exception:
            pass
            
        if not channel_id:
            search_resp = yt.search().list(
                part="snippet", q=handle, type="channel", maxResults=1
            ).execute()
            items = search_resp.get("items", [])
            if items:
                channel_id = items[0]["snippet"]["channelId"]
                
        if not channel_id:
            return {"error": f"Could not resolve channel for handle '{handle}'", "found": 0, "matched": 0}

        search_resp = yt.search().list(
            part="snippet", channelId=channel_id, type="video",
            order="date", maxResults=limit,
        ).execute()

        for item in search_resp.get("items", []):
            video_id = item["id"]["videoId"]
            thumbs = item.get("snippet", {}).get("thumbnails", {})
            thumb_url = (
                thumbs.get("high", {}).get("url") or
                thumbs.get("medium", {}).get("url") or
                thumbs.get("default", {}).get("url")
            )
            if not thumb_url:
                continue
                
            found += 1
            try:
                result = await detect_from_url(
                    url=thumb_url, platform="youtube",
                    page_url=f"https://www.youtube.com/watch?v={video_id}",
                    source_type="manual_account_check",
                )
                if result.matched:
                    matched += 1
            except Exception as e:
                logger.debug("Detection error for %s: %s", thumb_url, e)
    except Exception as e:
        return {"error": str(e), "found": found, "matched": matched}

    return {"found": found, "matched": matched}


async def download_video_preview(video_url: str) -> str | None:
    """
    Download first 10 seconds of a YouTube video at lowest quality.
    Returns path to temp .mp4 file, or None on failure.
    Caller is responsible for deleting the file after use.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp not installed. Run: pip install yt-dlp")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()

    ydl_opts = {
        "format":       "worst[ext=mp4]/worst",
        "outtmpl":      tmp_path,
        "quiet":        True,
        "no_warnings":  True,
        # Limit to first 10 seconds via postprocessor_args is unreliable;
        # use download_ranges instead (yt-dlp ≥2023.01)
        "download_ranges": lambda _, __: [{"start_time": 0, "end_time": 10}],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            return tmp_path
    except Exception as e:
        logger.debug("yt-dlp download failed for %s: %s", video_url, e)

    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    return None
