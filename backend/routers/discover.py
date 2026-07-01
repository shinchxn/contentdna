"""
backend/routers/discover.py

Endpoint to trigger the discovery layer for a registered asset.
Uses get_async_client() — the real async Supabase path, not the stub get_client().
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.store.supabase_client import get_async_client
from backend.discovery.orchestrator import discover_and_hunt

logger = logging.getLogger(__name__)
router = APIRouter(tags=["discovery"])


@router.post("/discover")
async def discover(asset_id: str):
    """
    Trigger the discovery layer for a specific asset.
    Fetches the real asset from Supabase, then runs Hashtag Crawling,
    Dorking, and Reverse Image Search concurrently, dispatching URLs
    to the Universal Web Hunter.

    Fails loudly (500) if Supabase is unreachable — does NOT substitute
    mock data so bugs surface immediately rather than hiding silently.
    """
    try:
        client = await get_async_client()
        res = await client.table("assets").select("*").eq("id", asset_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Asset not found")
        asset = res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching asset from DB: %s", e)
        raise HTTPException(status_code=500, detail="Database error")

    result = await discover_and_hunt(asset)
    return JSONResponse(result)
