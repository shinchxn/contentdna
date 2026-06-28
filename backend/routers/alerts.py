"""
backend/routers/alerts.py
──────────────────────────
GET /alerts         — Paginated list of alerts with optional filters
GET /alerts/{id}    — Single alert with joined asset details
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.store.supabase_client import get_alert, get_alerts

logger = logging.getLogger(__name__)
router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def list_alerts(
    owner_id:    Optional[str] = Query(default=None, description="Filter by owner UUID"),
    platform:    Optional[str] = Query(default=None, description="instagram | youtube | tiktok | reddit | web | live"),
    severity:    Optional[str] = Query(default=None, description="CRITICAL | HIGH | MEDIUM"),
    source_type: Optional[str] = Query(default=None, description="hunter | crawler | manual | dorking"),
    limit:       int           = Query(default=20, ge=1, le=100),
    offset:      int           = Query(default=0, ge=0),
):
    """
    List alerts with optional filtering and pagination.

    Filters are ANDed together.  Returns newest-first.
    Includes joined asset info (filename, media_type, storage_url, title).
    """
    try:
        alerts = await get_alerts(
            owner_id=owner_id,
            platform=platform,
            severity=severity,
            source_type=source_type,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("get_alerts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return JSONResponse({
        "alerts": alerts,
        "count":  len(alerts),
        "offset": offset,
        "limit":  limit,
    })


@router.get("/alerts/{alert_id}")
async def get_single_alert(alert_id: str):
    """
    Retrieve a single alert by UUID.

    Returns the alert record with embedded asset details.
    """
    try:
        alert = await get_alert(alert_id)
    except Exception as exc:
        logger.error("get_alert failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return JSONResponse(alert)
