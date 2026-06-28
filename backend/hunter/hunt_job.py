"""
backend/hunter/hunt_job.py
────────────────────────────
Celery task that orchestrates a full domain hunt.

Routing logic:
  URL type    → Primary extractor   → Fallback
  ──────────────────────────────────────────────
  YOUTUBE     → yt-dlp              → (none needed)
  LIVE        → streamlink          → (none needed)
  SOCIAL      → gallery-dl          → playwright
  DIRECT      → direct              → (none needed)
  STATIC      → scrapy              → playwright (if < 3 scrapy results)

For each MediaItem discovered:
  1. Load bytes (from item.file_bytes, item.path, or download from item.url)
  2. Run detect_from_file()
  3. Increment job progress counters in Supabase
  4. Clean up temp files

The task runs synchronously inside Celery (Celery workers use threads, not
asyncio by default).  We use asyncio.run() to call the async detection engine.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from celery import shared_task

from backend.hunter.url_classifier import URLType, classify_url
from backend.hunter.extractors.direct_extractor import extract_media_direct
from backend.hunter.extractors.gallerydl_extractor import extract_media_gallerydl
from backend.hunter.extractors.playwright_extractor import extract_media_playwright
from backend.hunter.extractors.scrapy_extractor import extract_media_scrapy
from backend.hunter.extractors.streamlink_extractor import extract_media_streamlink
from backend.hunter.extractors.ytdlp_extractor import extract_media_ytdlp
from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_item_bytes(item: MediaItem) -> tuple[Optional[bytes], str]:
    """
    Return (raw_bytes, media_type) for the given MediaItem.
    Downloads from item.url if neither item.path nor item.file_bytes is set.
    """
    import httpx

    if item.file_bytes:
        return item.file_bytes, item.media_type

    if item.path and os.path.exists(item.path):
        with open(item.path, "rb") as f:
            return f.read(), item.media_type

    if item.url:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(item.url)
                resp.raise_for_status()
            return resp.content, item.media_type
        except Exception as exc:
            logger.warning("Failed to download %s: %s", item.url, exc)

    return None, item.media_type


def _cleanup(item: MediaItem) -> None:
    """Remove temp file if it exists."""
    if item.path:
        try:
            os.unlink(item.path)
        except OSError:
            pass


async def _process_item(
    item: MediaItem,
    owner_id: str,
    platform: str,
) -> tuple[int, int]:
    """
    Load, detect, and clean up one MediaItem.
    Returns (media_found_delta, matches_found_delta).
    """
    from backend.detection.engine import detect_from_file

    file_bytes, media_type = await _load_item_bytes(item)
    if not file_bytes:
        return 0, 0

    result = await detect_from_file(
        file_bytes=file_bytes,
        media_type=media_type,
        source_url=item.url,
        page_url=item.page_url,
        platform=platform,
        source_type="hunter",
    )

    _cleanup(item)
    return 1, len(result.matches)


async def _run_hunt_async(
    job_id: str,
    seed_url: str,
    owner_id: str,
    max_depth: int,
    max_pages: int,
) -> None:
    """Async implementation of the hunt pipeline."""
    from backend.store.supabase_client import update_hunt_job

    # ── Mark running ────────────────────────────────────────────────────────
    await update_hunt_job(job_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    url_type = classify_url(seed_url)
    logger.info("Hunt %s: URL type=%s, seed=%s", job_id, url_type.value, seed_url)

    pages_crawled = 0
    media_found   = 0
    matches_found = 0

    # Determine platform label for alerts
    platform_map = {
        URLType.YOUTUBE: "youtube",
        URLType.LIVE:    "live",
        URLType.SOCIAL:  "web",
        URLType.DIRECT:  "web",
        URLType.STATIC:  "web",
    }
    platform = platform_map.get(url_type, "web")

    try:
        # ── Route to primary extractor ──────────────────────────────────────
        primary_items: list[MediaItem] = []

        if url_type == URLType.YOUTUBE:
            async for item in extract_media_ytdlp(seed_url):
                primary_items.append(item)

        elif url_type == URLType.LIVE:
            async for item in extract_media_streamlink(seed_url):
                primary_items.append(item)

        elif url_type == URLType.SOCIAL:
            async for item in extract_media_gallerydl(seed_url):
                primary_items.append(item)
            # Fallback to Playwright if gallery-dl got nothing
            if len(primary_items) < 3:
                logger.info("Hunt %s: gallery-dl fallback → playwright", job_id)
                async for item in extract_media_playwright(seed_url):
                    primary_items.append(item)

        elif url_type == URLType.DIRECT:
            async for item in extract_media_direct(seed_url):
                primary_items.append(item)

        else:  # STATIC
            scrapy_items: list[MediaItem] = []
            async for item in extract_media_scrapy(seed_url, max_depth, max_pages):
                scrapy_items.append(item)

            if len(scrapy_items) < 3:
                logger.info("Hunt %s: scrapy < 3 items → playwright fallback", job_id)
                async for item in extract_media_playwright(seed_url):
                    scrapy_items.append(item)

            primary_items = scrapy_items
            pages_crawled = max_pages  # scrapy handles pagination internally

        # ── Process each item ───────────────────────────────────────────────
        logger.info("Hunt %s: processing %d media items", job_id, len(primary_items))
        for item in primary_items:
            mf, mf_matches = await _process_item(item, owner_id, platform)
            media_found   += mf
            matches_found += mf_matches

            # Periodically update progress
            if (media_found % 10) == 0:
                await update_hunt_job(job_id, {
                    "media_found":   media_found,
                    "matches_found": matches_found,
                })

        # ── Mark done ───────────────────────────────────────────────────────
        await update_hunt_job(job_id, {
            "status":        "done",
            "pages_crawled": pages_crawled,
            "media_found":   media_found,
            "matches_found": matches_found,
            "completed_at":  datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "Hunt %s done: media=%d matches=%d", job_id, media_found, matches_found
        )

    except Exception as exc:
        logger.error("Hunt %s FAILED: %s", job_id, exc, exc_info=True)
        await update_hunt_job(job_id, {
            "status":       "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })


# ── Celery task ───────────────────────────────────────────────────────────────

@shared_task(name="hunt_job.run_hunt", bind=True, max_retries=0)
def run_hunt(
    self,
    job_id: str,
    seed_url: str,
    owner_id: str,
    max_depth: int = 3,
    max_pages: int = 100,
) -> None:
    """
    Celery task: run a full domain hunt.
    Called via run_hunt.delay(job_id, seed_url, owner_id, ...).
    """
    logger.info("Celery: starting hunt job %s for %s", job_id, seed_url)
    asyncio.run(_run_hunt_async(job_id, seed_url, owner_id, max_depth, max_pages))
