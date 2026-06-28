"""
backend/hunter/extractors/gallerydl_extractor.py
──────────────────────────────────────────────────
Uses gallery-dl (supports 300+ platforms including Instagram, Flickr, Pixiv,
Pinterest, DeviantArt, Twitter/X, etc.) to bulk-download media from a URL.

gallery-dl is particularly powerful for social media galleries — it handles
pagination, session cookies, and rate limiting automatically.

We set a temp output directory, run the extraction, then yield a MediaItem
for each downloaded file.  Files are the caller's responsibility to delete.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import AsyncGenerator, List

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def _run_gallerydl(url: str, output_dir: str) -> List[str]:
    """
    Run gallery-dl synchronously and return list of downloaded file paths.
    Import is deferred so that a missing install doesn't break the module.
    """
    try:
        import gallery_dl

        # gallery-dl config: set output path, disable post-processing
        config = {
            "extractor": {
                "base-directory": output_dir,
                "skip": False,
            },
            "output": {
                "mode": "null",   # suppress console output
            },
        }
        gallery_dl.config.set((), config)

        # Use the job API
        job = gallery_dl.job.DownloadJob(url)
        job.run()

        # Collect all downloaded files recursively
        downloaded: List[str] = []
        for root, _, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if os.path.getsize(fpath) > 512:   # skip tiny files
                    downloaded.append(fpath)
        return downloaded

    except Exception as exc:
        logger.error("gallery-dl error for %s: %s", url, exc)
        return []


async def extract_media_gallerydl(url: str) -> AsyncGenerator[MediaItem, None]:
    """
    Extract all media from *url* using gallery-dl.

    Yields a MediaItem for each downloaded image or video file.
    Unsupported URLs silently yield nothing.
    Callers must delete item.path after processing.
    """
    logger.info("GalleryDLExtractor: extracting from %s", url)
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_gallerydl_")
    loop = asyncio.get_event_loop()

    downloaded = await loop.run_in_executor(None, _run_gallerydl, url, tmp_dir)
    logger.debug("GalleryDL downloaded %d files from %s", len(downloaded), url)

    for fpath in downloaded:
        ext = os.path.splitext(fpath)[1].lower()
        if ext in IMAGE_EXTS:
            media_type = "image"
        elif ext in VIDEO_EXTS:
            media_type = "video"
        else:
            continue   # skip non-media files (e.g. metadata JSONs)

        yield MediaItem(
            url=url,
            path=fpath,
            page_url=url,
            media_type=media_type,
        )
