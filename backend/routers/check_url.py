"""
backend/routers/check_url.py
──────────────────────────────
POST /check-url — Check a remote URL for infringement.

Downloads the media at the given URL and runs the full detection pipeline.
Useful for: browser extension one-click checks, manual URL investigations,
or API consumers that already have the URL of suspect content.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from backend.detection.engine import detect_from_url

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detect"])


class CheckURLRequest(BaseModel):
    url: str
    platform: str = "web"
    page_url: str | None = None


def _result_to_dict(result) -> dict:
    return {
        "matched": result.matched,
        "processing_time_ms": result.processing_time_ms,
        "platform": result.platform,
        "source_type": result.source_type,
        "source_url": result.source_url,
        "page_url": result.page_url,
        "matches": [
            {
                "asset_id":            m.asset_id,
                "owner_id":            m.owner_id,
                "score":               m.score,
                "severity":            m.severity,
                "filename":            m.filename,
                "storage_url":         m.storage_url,
                "watermark_confirmed": m.watermark_confirmed,
            }
            for m in result.matches
        ],
    }


@router.post("/check-url")
async def check_url(body: CheckURLRequest):
    """
    Check a remote media URL for infringement.

    - **url**: Direct URL to an image or video
    - **platform**: One of: instagram | youtube | tiktok | reddit | web | live
    - **page_url**: Optional — the page where this media URL was found

    Downloads the content and runs the full detection pipeline.
    """
    logger.info("CheckURL: url=%s platform=%s", body.url, body.platform)

    try:
        result = await detect_from_url(
            url=body.url,
            platform=body.platform,
            page_url=body.page_url,
            source_type="manual",
        )
    except Exception as exc:
        logger.error("check-url detection failed for %s: %s", body.url, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {exc}"
        )

    return JSONResponse(_result_to_dict(result))
