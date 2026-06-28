"""
backend/hunter/extractors/gallerydl_extractor.py

Source: project/hunter/gallerydl_engine/gallery_dl/__init__.py → DownloadJob pattern
  - Copied: gallery_dl.config.load([]) + gallery_dl.config.set() + job.DownloadJob(url).run()
  - From __init__.py line 368: jobtype = job.DownloadJob; status = jobtype(url).run()
  - Modified: set base-directory to tmp_dir, walk files after run()
"""
import asyncio
import logging
import os
import tempfile
from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def _run_gallerydl_sync(url: str, output_dir: str) -> list:
    """
    Copied from gallery_dl/__init__.py line 368:
      jobtype = job.DownloadJob
      status = jobtype(url).run()

    Modified: configure base-directory before running.
    """
    try:
        import gallery_dl.config as gdl_config
        import gallery_dl.job as gdl_job

        gdl_config.load([])  # reset config
        gdl_config.set((), "base-directory", output_dir)
        gdl_config.set((), "directory", [])
        gdl_config.set(("output",), "mode", "null")

        gdl_job.DownloadJob(url).run()

        results = []
        for root, _, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if os.path.getsize(fpath) > 512:
                    results.append(fpath)
        return results
    except Exception as exc:
        logger.error("gallery-dl error for %s: %s", url, exc)
        return []


async def extract_media_gallerydl(url: str):
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_gallerydl_")
    loop = asyncio.get_event_loop()

    files = await loop.run_in_executor(None, _run_gallerydl_sync, url, tmp_dir)
    logger.debug("gallery-dl: %d files from %s", len(files), url)

    for fpath in files:
        ext = os.path.splitext(fpath)[1].lower()
        if ext in IMAGE_EXTS:
            media_type = "image"
        elif ext in VIDEO_EXTS:
            media_type = "video"
        else:
            continue
        yield MediaItem(url=url, path=fpath, page_url=url, media_type=media_type)
