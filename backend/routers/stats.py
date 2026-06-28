"""
backend/routers/stats.py
─────────────────────────
GET /stats — Dashboard stats for a content owner.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.store.supabase_client import get_stats

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stats"])


@router.get("/stats")
async def dashboard_stats(
    owner_id: str = Query(..., description="Owner UUID"),
):
    """
    Return comprehensive dashboard statistics for the given owner.

    Response structure:
    ```json
    {
        "total_assets": 42,
        "total_alerts": 187,
        "alerts_by_platform": {"instagram": 90, "youtube": 50, ...},
        "alerts_by_severity": {"CRITICAL": 12, "HIGH": 45, "MEDIUM": 130},
        "alerts_by_source":   {"hunter": 80, "crawler": 60, ...},
        "recent_alerts": [...]
    }
    ```
    """
    try:
        stats = await get_stats(owner_id)
    except Exception as exc:
        logger.error("get_stats failed for owner %s: %s", owner_id, exc)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return JSONResponse(stats)
