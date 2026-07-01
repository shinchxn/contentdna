"""
backend/routers/detect.py
──────────────────────────
POST /detect — Manual single-file infringement check.

Accepts a media file upload and runs it through the full detection pipeline.
Returns a structured JSON result with all matches, scores, and severities.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.detection.engine import DetectionResult, detect_from_file

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detect"])

_IMAGE_CTS = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/avif", "image/heic",
}
_VIDEO_CTS = {
    "video/mp4", "video/webm", "video/quicktime",
    "video/x-msvideo", "video/x-matroska",
}


def _media_type_from_upload(upload: UploadFile) -> str:
    ct = (upload.content_type or "").lower().split(";")[0].strip()
    if ct in _IMAGE_CTS or ct.startswith("image/"):
        return "image"
    if ct in _VIDEO_CTS or ct.startswith("video/"):
        return "video"
    # Fallback to filename
    fname = (upload.filename or "").lower()
    if any(fname.endswith(e) for e in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
        return "image"
    if any(fname.endswith(e) for e in [".mp4", ".webm", ".mov", ".avi", ".mkv"]):
        return "video"
    raise HTTPException(
        status_code=415,
        detail="Unsupported file type. Upload an image or video."
    )


def _result_to_dict(result: DetectionResult) -> dict:
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


@router.post("/detect")
async def detect_media(
    file: UploadFile = File(...),
):
    """
    Check a media file against all registered assets.

    - **file**: Image or video file

    Returns match results with score, severity, and matched asset details.
    """
    media_type = _media_type_from_upload(file)
    file_bytes = await file.read()

    logger.info("Detect: file=%s type=%s size=%d",
                file.filename, media_type, len(file_bytes))

    try:
        result = await detect_from_file(
            file_bytes=file_bytes,
            media_type=media_type,
            source_type="manual",
            platform="web",
        )
    except Exception as exc:
        logger.error("Detection failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Detection error: {exc}")

    return JSONResponse(_result_to_dict(result))
