"""
backend/crawlers/worker.py
───────────────────────────
Celery application definition.

This is the entry point for the Celery worker and beat scheduler.
It auto-discovers tasks from backend.hunter.hunt_job.

Run with:
    celery -A backend.crawlers.worker worker -c 4 --loglevel=info
    celery -A backend.crawlers.worker beat  --loglevel=info
    celery -A backend.crawlers.worker flower --port=5555
"""

from __future__ import annotations

from celery import Celery
from backend.config import REDIS_URL

app = Celery(
    "contentdna",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.hunter.hunt_job"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,       # one task at a time per worker slot
    task_acks_late=True,                # ack after task completes (not before)
    task_reject_on_worker_lost=True,
)

# ── Scheduled tasks (beat) ────────────────────────────────────────────────────
# Person 2 can add platform crawler schedules here later.
app.conf.beat_schedule = {}

if __name__ == "__main__":
    app.start()
