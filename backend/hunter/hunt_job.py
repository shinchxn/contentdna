"""
backend/hunter/hunt_job.py

Source: project/reference/crawler/ → concept: URL queue + processing loop
Modified: replaced old crawler with new extractor routing, made Celery task,
          updates hunt_jobs table at each step.
"""
import asyncio
import logging
from datetime import datetime, timezone

# pyrefly: ignore [missing-import]
from celery import shared_task
from backend.config import REDIS_URL
from backend.hunter.url_classifier import URLType, classify_url

logger = logging.getLogger(__name__)


async def _process_item(item, owner_id: str, platform: str) -> tuple[int, int]:
    """Load bytes, detect, return (media_found++, matches_found++)."""
    from backend.detection.engine import detect_from_file
    import os

    file_bytes = None
    if item.file_bytes:
        file_bytes = item.file_bytes
    elif item.path and os.path.exists(item.path):
        with open(item.path, "rb") as f:
            file_bytes = f.read()
    elif item.url:
        # pyrefly: ignore [missing-import]
        import httpx
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                r = await client.get(item.url)
                r.raise_for_status()
                file_bytes = r.content
        except Exception as exc:
            logger.warning("Failed to download %s: %s", item.url, exc)

    if not file_bytes:
        return 0, 0

    result = await detect_from_file(
        file_bytes=file_bytes,
        media_type=item.media_type,
        source_url=item.url,
        page_url=item.page_url,
        platform=platform,
        source_type="hunter",
    )

    # Clean up temp file
    if item.path:
        try:
            os.unlink(item.path)
        except OSError:
            pass

    return 1, len(result.matches)


async def _run_hunt(job_id: str, seed_url: str, owner_id: str,
                    max_depth: int, max_pages: int):
    from backend.store.supabase_client import update_hunt_job
    from backend.hunter.extractors.direct_extractor import extract_media_direct
    from backend.hunter.extractors.ytdlp_extractor import extract_media_ytdlp
    from backend.hunter.extractors.gallerydl_extractor import extract_media_gallerydl
    from backend.hunter.extractors.playwright_extractor import extract_media_playwright
    from backend.hunter.extractors.scrapy_extractor import extract_media_scrapy
    from backend.hunter.extractors.streamlink_extractor import extract_media_streamlink

    # 1. update_hunt_job(job_id, {status: "running", started_at: now})
    await update_hunt_job(job_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    # 2. url_type = classify_url(seed_url)
    url_type = classify_url(seed_url)
    platform_map = {
        URLType.YOUTUBE: "youtube",
        URLType.LIVE: "live",
        URLType.SOCIAL: "web",
        URLType.DIRECT: "web",
        URLType.STATIC: "web",
    }
    platform = platform_map.get(url_type, "web")
    pages_crawled = media_found = matches_found = 0

    try:
        # 3. Route to correct extractor
        all_items = []

        if url_type == URLType.YOUTUBE:
            async for item in extract_media_ytdlp(seed_url):
                all_items.append(item)

        elif url_type == URLType.LIVE:
            async for item in extract_media_streamlink(seed_url):
                all_items.append(item)

        elif url_type == URLType.SOCIAL:
            async for item in extract_media_gallerydl(seed_url):
                all_items.append(item)
            if len(all_items) < 3:
                async for item in extract_media_playwright(seed_url):
                    all_items.append(item)

        elif url_type == URLType.DIRECT:
            async for item in extract_media_direct(seed_url):
                all_items.append(item)

        else:  # STATIC
            async for item in extract_media_scrapy(seed_url, max_depth, max_pages):
                all_items.append(item)
            if len(all_items) < 3:
                async for item in extract_media_playwright(seed_url):
                    all_items.append(item)
            pages_crawled = max_pages

        # 4. For each MediaItem: normalize → fingerprint → detect → update
        for item in all_items:
            mf, mm = await _process_item(item, owner_id, platform)
            media_found   += mf
            matches_found += mm

            # update_hunt_job(job_id, {pages_crawled++, media_found++, matches_found++})
            if media_found % 5 == 0:
                await update_hunt_job(job_id, {
                    "pages_crawled": pages_crawled,
                    "media_found":   media_found,
                    "matches_found": matches_found,
                })

        # 5. update_hunt_job(job_id, {status: "done", completed_at: now})
        await update_hunt_job(job_id, {
            "status":        "done",
            "pages_crawled": pages_crawled,
            "media_found":   media_found,
            "matches_found": matches_found,
            "completed_at":  datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        logger.error("Hunt %s failed: %s", job_id, exc, exc_info=True)
        await update_hunt_job(job_id, {
            "status":       "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })


@shared_task(name="hunt_job.run_hunt", bind=True, max_retries=0)
def run_hunt(self, job_id: str, seed_url: str, owner_id: str,
             max_depth: int = 3, max_pages: int = 100):
    """
    Celery task. Runs the async hunt pipeline via asyncio.run().
    Source concept: project/reference/crawler/ — URL queue + processing loop
    Modified: extractor routing + Celery wrapping.
    """
    asyncio.run(_run_hunt(job_id, seed_url, owner_id, max_depth, max_pages))
