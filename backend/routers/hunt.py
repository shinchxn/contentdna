"""
backend/routers/hunt.py
─────────────────────────
POST /hunt                   — Start a new background hunt job
GET  /hunt/status/{job_id}   — Poll job status
POST /hunt/{platform}        — Manually trigger a specific platform crawl
"""

from __future__ import annotations

import logging

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

from backend.config import HUNTER_MAX_DEPTH, HUNTER_MAX_PAGES
from backend.store.supabase_client import get_hunt_job, insert_hunt_job

logger = logging.getLogger(__name__)
router = APIRouter(tags=["hunt"])


class HuntRequest(BaseModel):
    url: str
    owner_id: str
    max_depth: int = HUNTER_MAX_DEPTH
    max_pages: int = HUNTER_MAX_PAGES


@router.post("/hunt")
async def start_hunt(body: HuntRequest):
    """
    Start a background domain hunt.

    - **url**: Seed URL (domain, YouTube channel, social page, etc.)
    - **owner_id**: UUID of the content owner
    - **max_depth**: How many link-hops deep to crawl (default 3)
    - **max_pages**: Maximum pages to crawl (default 100)

    Returns job_id immediately; poll /hunt/status/{job_id} for progress.
    """
    logger.info("Starting hunt: url=%s owner=%s depth=%d pages=%d",
                body.url, body.owner_id, body.max_depth, body.max_pages)

    # Create the job record
    try:
        job = await insert_hunt_job({
            "owner_id": body.owner_id,
            "seed_url": body.url,
            "status":   "pending",
        })
    except Exception as exc:
        logger.error("Failed to create hunt job: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create hunt job: {exc}")

    job_id = job["id"]

    # Enqueue the Celery task
    try:
        from backend.crawlers.worker import run_hunt_task
        run_hunt_task.delay(job_id, body.url, body.owner_id, body.max_depth, body.max_pages)
    except Exception as exc:
        logger.error("Failed to enqueue hunt task: %s", exc)
        # Update job to failed so UI isn't stuck
        from backend.store.supabase_client import update_hunt_job
        await update_hunt_job(job_id, {"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Task queue error: {exc}")

    logger.info("Hunt enqueued: job_id=%s", job_id)
    return JSONResponse({"job_id": job_id, "status": "pending"})


@router.get("/hunt/status/{job_id}")
async def get_hunt_status(job_id: str):
    """
    Get the current status and progress of a hunt job.

    Returns the full hunt_jobs record including pages_crawled, media_found,
    matches_found, and status (pending | running | done | failed).
    """
    job = await get_hunt_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Hunt job {job_id} not found")
    return JSONResponse(job)


# ── Per-platform manual trigger ────────────────────────────────────────────────
# Declared AFTER /hunt/status/{job_id} so FastAPI matches in correct order.
# /hunt/{platform} is one path segment (e.g. /hunt/reddit),
# /hunt/status/{job_id} is two segments — no collision, but keep ordering clean.

_PLATFORM_TASKS = {}  # populated lazily to avoid heavy imports at startup


def _get_platform_task(platform: str):
    if not _PLATFORM_TASKS:
        from backend.crawlers.worker import (
            crawl_reddit_task,
            crawl_youtube_task,
            crawl_instagram_task,
            crawl_tiktok_task,
        )
        _PLATFORM_TASKS.update({
            "reddit":    crawl_reddit_task,
            "youtube":   crawl_youtube_task,
            "instagram": crawl_instagram_task,
            "tiktok":    crawl_tiktok_task,
        })
    return _PLATFORM_TASKS.get(platform)


@router.post("/hunt/{platform}")
async def trigger_platform_crawl(platform: str):
    """
    Manually trigger an immediate crawl for a specific platform.
    Used by the Monitor page "Trigger Now" button.
    """
    task = _get_platform_task(platform)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    async_result = task.delay()
    logger.info("Platform crawl triggered: platform=%s task_id=%s", platform, async_result.id)
    return JSONResponse({"platform": platform, "task_id": async_result.id, "status": "triggered"})
