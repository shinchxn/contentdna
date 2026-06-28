"""
backend/hunter/extractors/ytdlp_extractor.py

Source: project/hunter/ytdlp_engine/yt_dlp/ → README + YoutubeDL options pattern
  - Copied: ydl_opts dict pattern (format, outtmpl, quiet, no_warnings)
  - Copied: with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.extract_info()
  - Modified: yield thumbnail as image MediaItem, then download short clip
"""
import asyncio
import logging
import os
import tempfile
import yt_dlp
from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)


def _extract_info_sync(url: str) -> dict:
    """
    Copied pattern from yt_dlp README:
      with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
          info = ydl.extract_info(url, download=False)
    """
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _download_clip_sync(url: str, out_path: str) -> bool:
    """
    Copied pattern from yt_dlp README:
      ydl_opts = {"format": "worst[ext=mp4]/worst", "outtmpl": path}
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          ydl.download([url])
    """
    ydl_opts = {
        "format": "worst[ext=mp4]/worst",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1024
    except Exception as exc:
        logger.debug("yt-dlp download failed: %s", exc)
        return False


async def extract_media_ytdlp(url: str):
    loop = asyncio.get_event_loop()
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_ytdlp_")

    # Get metadata + thumbnail URL
    info = await loop.run_in_executor(None, _extract_info_sync, url)

    # Yield thumbnail as image MediaItem
    thumbnail_url = info.get("thumbnail")
    if thumbnail_url:
        yield MediaItem(url=thumbnail_url, path=None, page_url=url, media_type="image")

    # Download lowest-quality clip
    clip_path = os.path.join(tmp_dir, "clip.mp4")
    success = await loop.run_in_executor(None, _download_clip_sync, url, clip_path)
    if success:
        yield MediaItem(url=url, path=clip_path, page_url=url, media_type="video")
