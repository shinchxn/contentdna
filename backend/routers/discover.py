"""
backend/routers/discover.py

Endpoint to trigger the discovery layer for a registered asset.
"""
from fastapi import APIRouter, HTTPException
from backend.store.supabase_client import get_client
from backend.discovery.orchestrator import discover_and_hunt
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])

@router.post("/discover")
async def discover(asset_id: str):
    """
    Trigger the discovery layer for a specific asset.
    Runs Hashtag Crawling, Dorking, and Reverse Image Search concurrently.
    Dispatches URLs to the Universal Web Hunter.
    """
    supabase = get_client()
    if not supabase:
        # Fallback if DB is not configured (e.g., prototype mode)
        logger.warning("Supabase not configured, using mock asset for discovery test.")
        asset = {
            "id": asset_id,
            "title": "sports highlights",
            "owner_domain": "example.com",
            "storage_url": "",
            "owner_id": "demo"
        }
    else:
        try:
            res = supabase.table("assets").select("*").eq("id", asset_id).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="Asset not found")
            asset = res.data[0]
        except Exception as e:
            logger.error("Error fetching asset from DB: %s", e)
            raise HTTPException(status_code=500, detail="Database error")

    result = await discover_and_hunt(asset)
    return result
