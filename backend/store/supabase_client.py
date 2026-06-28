"""
backend/store/supabase_client.py
──────────────────────────────────
Single-file Supabase gateway — all DB reads and writes go through here.

Design principles:
  - One lazy singleton client (get_client()), created once per process.
  - All public functions are async coroutines to match FastAPI's async workers.
    Supabase-py 2.x uses httpx under the hood and supports await natively.
  - Each function does exactly one thing and returns plain dicts / lists.
  - Errors from Supabase propagate as exceptions; callers decide how to handle.

Table layout (see schema.sql):
  assets       — registered media fingerprints
  alerts       — infringement detections
  hunt_jobs    — background crawl job tracking
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# pyrefly: ignore [missing-import]
from supabase import AsyncClient, create_async_client

from backend.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

_client: Optional[AsyncClient] = None


# ── Client singleton ─────────────────────────────────────────────────────────

async def get_async_client() -> AsyncClient:
    """Lazy-init the async Supabase client (one per process)."""
    global _client
    if _client is None:
        logger.info("Initialising Supabase async client")
        _client = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def get_client():
    """
    Synchronous accessor used only by the startup lifespan hook for eager
    validation.  Returns None — the real initialisation is async.
    Actual DB calls always go through get_async_client().
    """
    logger.info("Supabase connection will be established on first async call.")
    return None


# ── Assets ────────────────────────────────────────────────────────────────────

async def insert_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new asset record.

    Required keys: owner_id, filename, media_type, storage_url,
                   phash, faiss_id, title
    Optional keys: watermark_id

    Returns the inserted row (with generated id, created_at, etc.).
    """
    client = await get_async_client()
    response = await client.table("assets").insert(data).execute()
    return response.data[0]


async def get_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single asset by UUID. Returns None if not found."""
    client = await get_async_client()
    response = (
        await client.table("assets")
        .select("*")
        .eq("id", asset_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


async def get_assets(
    owner_id: str,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Paginated asset list for an owner, newest first."""
    client = await get_async_client()
    response = (
        await client.table("assets")
        .select("*")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data or []


# ── Alerts ────────────────────────────────────────────────────────────────────

async def insert_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new alert record.

    Required keys: asset_id, owner_id, source_type, platform,
                   source_url, match_score, severity
    Optional keys: page_url, thumbnail_url, watermark_confirmed, crawled_at
    """
    client = await get_async_client()
    response = await client.table("alerts").insert(data).execute()
    return response.data[0]


async def get_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single alert by UUID, joining the parent asset's info.
    Returns None if not found.
    """
    client = await get_async_client()
    response = (
        await client.table("alerts")
        .select("*, assets(id, filename, media_type, storage_url, phash, title)")
        .eq("id", alert_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


async def get_alerts(
    owner_id: Optional[str] = None,
    platform: Optional[str] = None,
    severity: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Paginated alert query with optional filters.
    Results are ordered newest-first.
    """
    client = await get_async_client()
    query = (
        client.table("alerts")
        .select("*, assets(filename, media_type, storage_url, title)")
        .order("created_at", desc=True)
    )
    if owner_id:
        query = query.eq("owner_id", owner_id)
    if platform:
        query = query.eq("platform", platform)
    if severity:
        query = query.eq("severity", severity)
    if source_type:
        query = query.eq("source_type", source_type)

    response = await query.range(offset, offset + limit - 1).execute()
    return response.data or []


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_stats(owner_id: str) -> Dict[str, Any]:
    """
    Return a comprehensive stats dict for the dashboard.

    Structure:
    {
        total_assets:       int,
        total_alerts:       int,
        alerts_by_platform: {instagram, youtube, tiktok, reddit, web, live},
        alerts_by_severity: {CRITICAL, HIGH, MEDIUM},
        alerts_by_source:   {hunter, crawler, manual, dorking},
        recent_alerts:      [last 5 alert records]
    }
    """
    client = await get_async_client()

    # Total assets
    assets_resp = (
        await client.table("assets")
        .select("id", count="exact")
        .eq("owner_id", owner_id)
        .execute()
    )
    total_assets = assets_resp.count or 0

    # All alerts for this owner (for aggregation)
    alerts_resp = (
        await client.table("alerts")
        .select("platform, severity, source_type, created_at")
        .eq("owner_id", owner_id)
        .execute()
    )
    all_alerts = alerts_resp.data or []
    total_alerts = len(all_alerts)

    alerts_by_platform: Dict[str, int] = {
        "instagram": 0, "youtube": 0, "tiktok": 0,
        "reddit": 0, "web": 0, "live": 0,
    }
    alerts_by_severity: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
    alerts_by_source:   Dict[str, int] = {
        "hunter": 0, "crawler": 0, "manual": 0, "dorking": 0,
    }

    for alert in all_alerts:
        plat = alert.get("platform")
        if plat in alerts_by_platform:
            alerts_by_platform[plat] += 1
        sev = alert.get("severity")
        if sev in alerts_by_severity:
            alerts_by_severity[sev] += 1
        src = alert.get("source_type")
        if src in alerts_by_source:
            alerts_by_source[src] += 1

    # Recent alerts (last 5)
    recent_resp = (
        await client.table("alerts")
        .select("*, assets(filename, media_type, storage_url, title)")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    active_jobs_resp = (
        await client.table("hunt_jobs")
        .select("id", count="exact")
        .eq("owner_id", owner_id)
        .eq("status", "running")
        .execute()
    )
    active_hunt_jobs = active_jobs_resp.count or 0

    return {
        "total_assets": total_assets,
        "total_alerts": total_alerts,
        "alerts_by_platform": alerts_by_platform,
        "alerts_by_severity": alerts_by_severity,
        "alerts_by_source": alerts_by_source,
        "recent_alerts": recent_resp.data or [],
        "active_hunt_jobs": active_hunt_jobs,
    }


# ── File Storage ──────────────────────────────────────────────────────────────

async def upload_file(
    file_bytes: bytes,
    bucket: str,
    path: str,
) -> str:
    """
    Upload *file_bytes* to Supabase Storage at *bucket/path*.

    Returns the public URL of the uploaded file.
    """
    client = await get_async_client()
    await client.storage.from_(bucket).upload(
        path,
        file_bytes,
        {"content-type": "application/octet-stream", "upsert": "true"},
    )
    url_response = client.storage.from_(bucket).get_public_url(path)
    return url_response


# ── Hunt Jobs ─────────────────────────────────────────────────────────────────

async def insert_hunt_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new hunt_job record. Returns the inserted row."""
    client = await get_async_client()
    response = await client.table("hunt_jobs").insert(data).execute()
    return response.data[0]


async def get_hunt_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a hunt_job by UUID. Returns None if not found."""
    client = await get_async_client()
    response = (
        await client.table("hunt_jobs")
        .select("*")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


async def update_hunt_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Apply *updates* dict to a hunt_job row."""
    client = await get_async_client()
    await (
        client.table("hunt_jobs")
        .update(updates)
        .eq("id", job_id)
        .execute()
    )
