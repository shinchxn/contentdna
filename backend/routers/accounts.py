"""
backend/routers/accounts.py
─────────────────────────────
POST   /accounts/check   — on-demand check of one account, runs synchronously
POST   /accounts         — add an account to the persistent watchlist
GET    /accounts         — list watched accounts for an owner
DELETE /accounts/{id}    — remove from watchlist
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["accounts"])

_CHECK_FUNCTIONS = {}  # populated lazily below to avoid heavy imports at startup


def _get_check_fn(platform: str):
    if not _CHECK_FUNCTIONS:
        from backend.crawlers.reddit import check_reddit_account
        from backend.crawlers.instagram import check_instagram_account
        from backend.crawlers.youtube import check_youtube_account
        from backend.crawlers.tiktok import check_tiktok_account
        _CHECK_FUNCTIONS.update({
            "reddit": check_reddit_account,
            "instagram": check_instagram_account,
            "youtube": check_youtube_account,
            "tiktok": check_tiktok_account,
        })
    return _CHECK_FUNCTIONS.get(platform)


class CheckAccountRequest(BaseModel):
    owner_id: str
    platform: str   # instagram | youtube | tiktok | reddit
    handle: str
    limit: int = 25


@router.post("/accounts/check")
async def check_account(body: CheckAccountRequest):
    """
    Run an immediate, synchronous check of one account. Intended for small N
    (single account, capped result limit) — should return in low single-digit
    seconds for most platforms. Does NOT add to the watchlist automatically;
    call POST /accounts separately (or pass save=true — see note below) if
    the user wants it watched going forward.
    """
    fn = _get_check_fn(body.platform)
    if not fn:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {body.platform}")

    result = await fn(handle=body.handle, owner_id=body.owner_id, limit=body.limit)

    if "error" in result:
        # Surface platform errors (bad credentials, account not found, etc.)
        # as a 200 with an error field, not a 500 — this is an expected,
        # recoverable outcome the frontend should display inline, not treat
        # as a server failure.
        return JSONResponse({
            "platform": body.platform, "handle": body.handle,
            "found": result.get("found", 0), "matched": result.get("matched", 0),
            "error": result["error"],
        })

    return JSONResponse({
        "platform": body.platform, "handle": body.handle,
        "found": result["found"], "matched": result["matched"],
    })


class WatchAccountRequest(BaseModel):
    owner_id: str
    platform: str
    handle: str
    label: str | None = None


@router.post("/accounts")
async def add_watched_account(body: WatchAccountRequest):
    from backend.store.supabase_client import insert_watched_account
    try:
        row = await insert_watched_account({
            "owner_id": body.owner_id, "platform": body.platform,
            "handle": body.handle, "label": body.label, "source": "manual",
        })
    except Exception as exc:
        # Likely a UNIQUE constraint violation if already watched
        raise HTTPException(status_code=409, detail=f"Could not add account: {exc}")
    return JSONResponse(row)


@router.get("/accounts")
async def list_watched_accounts(
    owner_id: str = Query(...),
    platform: str | None = Query(default=None),
):
    from backend.store.supabase_client import get_watched_accounts
    accounts = await get_watched_accounts(owner_id=owner_id, platform=platform)
    return JSONResponse({"accounts": accounts, "count": len(accounts)})


@router.delete("/accounts/{account_id}")
async def remove_watched_account(account_id: str):
    from backend.store.supabase_client import delete_watched_account
    await delete_watched_account(account_id)
    return JSONResponse({"deleted": True, "id": account_id})
