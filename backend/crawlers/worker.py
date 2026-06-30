"""
backend/crawlers/worker.py

Celery application + beat schedule.
All platform crawlers run every 15 minutes (900 seconds).
Hunt jobs are dispatched here from the /hunt API endpoint.
"""
import asyncio
import logging

from celery import Celery
from backend.config import REDIS_URL

logger = logging.getLogger(__name__)

app = Celery(
    "contentdna",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# ── Beat schedule: crawlers every 15 minutes ──────────────────────────────────
app.conf.beat_schedule = {
    "crawl-reddit": {
        "task":     "crawl_reddit_task",
        "schedule": 900.0,  # 15 minutes
    },
    "crawl-youtube": {
        "task":     "crawl_youtube_task",
        "schedule": 900.0,
    },
    "crawl-instagram": {
        "task":     "crawl_instagram_task",
        "schedule": 900.0,
    },
    "crawl-tiktok": {
        "task":     "crawl_tiktok_task",
        "schedule": 900.0,
    },
}


# ── Platform crawler tasks ─────────────────────────────────────────────────────

@app.task(name="crawl_reddit_task", bind=True, max_retries=2, default_retry_delay=60)
def crawl_reddit_task(self):
    try:
        from backend.crawlers.reddit import crawl_reddit
        asyncio.run(crawl_reddit())
    except Exception as exc:
        logger.error("Reddit crawler error: %s", exc)
        raise self.retry(exc=exc)


@app.task(name="crawl_youtube_task", bind=True, max_retries=2, default_retry_delay=60)
def crawl_youtube_task(self):
    try:
        from backend.crawlers.youtube import crawl_youtube
        asyncio.run(crawl_youtube())
    except Exception as exc:
        logger.error("YouTube crawler error: %s", exc)
        raise self.retry(exc=exc)


@app.task(name="crawl_instagram_task", bind=True, max_retries=2, default_retry_delay=60)
def crawl_instagram_task(self):
    try:
        from backend.crawlers.instagram import crawl_instagram
        asyncio.run(crawl_instagram())
    except Exception as exc:
        logger.error("Instagram crawler error: %s", exc)
        raise self.retry(exc=exc)


@app.task(name="crawl_tiktok_task", bind=True, max_retries=2, default_retry_delay=60)
def crawl_tiktok_task(self):
    try:
        from backend.crawlers.tiktok import crawl_tiktok
        asyncio.run(crawl_tiktok())
    except Exception as exc:
        logger.error("TikTok crawler error: %s", exc)
        raise self.retry(exc=exc)


# ── Hunt job task (dispatched by /hunt API endpoint) ──────────────────────────

@app.task(name="run_hunt", bind=True, max_retries=1, default_retry_delay=30)
def run_hunt_task(
    self,
    job_id: str,
    seed_url: str,
    owner_id: str,
    max_depth: int = 3,
    max_pages: int = 100,
):
    """
    Deep web crawl hunt job.
    Dispatched by POST /hunt in backend/routers/hunt.py.
    """
    try:
        from backend.hunter.hunt_job import run_hunt
        asyncio.run(run_hunt(job_id, seed_url, owner_id, max_depth, max_pages))
    except Exception as exc:
        logger.error("Hunt job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc)
