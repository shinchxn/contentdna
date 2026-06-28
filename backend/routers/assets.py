"""
backend/routers/assets.py
GET /assets — Paginated list of registered assets for an owner.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from backend.store.supabase_client import get_assets

logger = logging.getLogger(__name__)
router = APIRouter(tags=["assets"])


@router.get("/assets")
async def list_assets(
    owner_id: str = Query(..., description="Owner UUID"),
    limit:    int = Query(default=20, ge=1, le=100),
    offset:   int = Query(default=0, ge=0),
):
    """
    List registered assets for an owner, newest-first.
    """
    try:
        assets = await get_assets(owner_id=owner_id, limit=limit, offset=offset)
    except Exception as exc:
        logger.error("get_assets failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
    return JSONResponse({"assets": assets, "count": len(assets), "offset": offset, "limit": limit})
