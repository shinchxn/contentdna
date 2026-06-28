"""
backend/hunter/extractors/ytdlp_extractor.py
──────────────────────────────────────────────
Uses yt-dlp (supports 1000+ platforms) to extract media from video URLs.

Two items are yielded per URL:
  1. Thumbnail — the best available thumbnail image (fast, no video download)
  2. Video clip — first ~10 seconds of the lowest-quality stream (144p or worst)
     saved to a temp file.  This is enough for CLIP fingerprinting.

Why both?
  The thumbnail is the "face" of the video — it's usually the most distinctive
  frame and will match against registered thumbnails.
  The short video clip catches cases where the thumbnail was changed but the
  video content is still stolen.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import AsyncGenerator

import yt_dlp

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)


def _download_thumbnail(url: str, tmp_dir: str) -> str | None:
    """Download the best thumbnail to tmp_dir. Returns local path or None."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writethumbnail": True,
        "outtmpl": os.path.join(tmp_dir, "thumbnail"),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # yt-dlp appends the format extension automatically
        for fname in os.listdir(tmp_dir):
            if fname.startswith("thumbnail"):
                return os.path.join(tmp_dir, fname)
    except Exception as exc:
        logger.debug("Thumbnail download failed for %s: %s", url, exc)
    return None


def _download_clip(url: str, tmp_dir: str, duration_sec: int = 10) -> str | None:
    """Download the first *duration_sec* seconds at lowest quality. Returns path or None."""
    out_path = os.path.join(tmp_dir, "clip.mp4")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "worstvideo[ext=mp4]/worst[ext=mp4]/worst",
        "outtmpl": out_path,
        "postprocessors": [],
        # External downloader args to limit download time / size
        "external_downloader": "ffmpeg",
        "external_downloader_args": ["-ss", "0", "-t", str(duration_sec)],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            return out_path
    except Exception as exc:
        logger.debug("Clip download failed for %s: %s", url, exc)
    return None


async def extract_media_ytdlp(url: str) -> AsyncGenerator[MediaItem, None]:
    """
    Extract media from *url* using yt-dlp.

    Yields
    ------
    MediaItem
        Up to 2 items: thumbnail (image) + short clip (video).
        Callers must delete item.path when finished.
    """
    logger.info("YtdlpExtractor: extracting from %s", url)
    loop = asyncio.get_event_loop()
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_ytdlp_")

    try:
        # ── Thumbnail ──────────────────────────────────────────────────────
        thumb_path = await loop.run_in_executor(
            None, _download_thumbnail, url, tmp_dir
        )
        if thumb_path and os.path.exists(thumb_path):
            yield MediaItem(
                url=url,
                path=thumb_path,
                page_url=url,
                media_type="image",
            )

        # ── Short video clip ───────────────────────────────────────────────
        clip_path = await loop.run_in_executor(
            None, _download_clip, url, tmp_dir
        )
        if clip_path and os.path.exists(clip_path):
            yield MediaItem(
                url=url,
                path=clip_path,
                page_url=url,
                media_type="video",
            )

    except Exception as exc:
        logger.error("YtdlpExtractor fatal error for %s: %s", url, exc)
    # NOTE: tmp_dir and its contents are NOT cleaned up here —
    # the hunt_job runner deletes item.path after detection is done.
