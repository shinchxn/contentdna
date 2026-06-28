"""
backend/routers/upload.py
──────────────────────────
POST /upload — Register a new media asset.

Full pipeline:
  1. Accept multipart: file + owner_id + title
  2. Detect media type from Content-Type header
  3. Upload original bytes to Supabase Storage bucket "assets"
  4. Fingerprint: CLIP embedding + pHash
  5. Embed invisible watermark (images only)
  6. Upload watermarked version to Storage
  7. Add CLIP vector to FAISS index → get faiss_id
  8. Insert asset record in Supabase
  9. Return structured response
"""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.fingerprint.clip_encoder import encode_image
from backend.fingerprint.phash_encoder import encode_phash
from backend.fingerprint.video_processor import extract_video_embedding, extract_video_phash
from backend.fingerprint.watermark import embed_watermark
from backend.store.faiss_store import add_asset
from backend.store.supabase_client import insert_asset, upload_file

logger = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])

_BUCKET = "assets"
_IMAGE_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/avif", "image/heic",
}
_VIDEO_CONTENT_TYPES = {
    "video/mp4", "video/webm", "video/quicktime",
    "video/x-msvideo", "video/x-matroska", "video/mpeg",
}


def _detect_media_type(content_type: str, filename: str) -> str:
    ct = content_type.lower().split(";")[0].strip()
    if ct in _IMAGE_CONTENT_TYPES or ct.startswith("image/"):
        return "image"
    if ct in _VIDEO_CONTENT_TYPES or ct.startswith("video/"):
        return "video"
    # Fallback: check filename extension
    fname_lower = filename.lower()
    if any(fname_lower.endswith(ext) for ext in
           [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"]):
        return "image"
    if any(fname_lower.endswith(ext) for ext in
           [".mp4", ".webm", ".mov", ".avi", ".mkv"]):
        return "video"
    raise HTTPException(
        status_code=415,
        detail=f"Unsupported media type: {content_type}. "
               "Upload an image (jpg/png/webp) or video (mp4/webm/mov)."
    )


@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    title: str = Form(default=""),
):
    """
    Register a new media asset.

    - **file**: Image or video file (multipart/form-data)
    - **owner_id**: UUID of the content owner (from Supabase auth)
    - **title**: Optional title / description

    Returns the registered asset record including asset_id and FAISS id.
    """
    asset_id = str(uuid.uuid4())
    file_bytes = await file.read()
    filename   = file.filename or "upload"
    media_type = _detect_media_type(file.content_type or "", filename)

    logger.info("Upload: asset_id=%s owner=%s type=%s filename=%s size=%d bytes",
                asset_id, owner_id, media_type, filename, len(file_bytes))

    # ── Step 3: Upload original to Storage ─────────────────────────────────
    original_path = f"{owner_id}/{asset_id}/original_{filename}"
    try:
        storage_url = await upload_file(file_bytes, _BUCKET, original_path)
    except Exception as exc:
        logger.error("Storage upload failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {exc}")

    # ── Steps 4–6: Fingerprint + watermark ─────────────────────────────────
    import tempfile, os
    from PIL import Image

    suffix = ".jpg" if media_type == "image" else ".mp4"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    watermark_embedded = False
    phash = "0000000000000000"

    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(file_bytes)

        if media_type == "image":
            pil_image  = Image.open(tmp_path).convert("RGB")
            clip_vector = encode_image(pil_image)
            phash      = encode_phash(pil_image)

            # Embed watermark
            try:
                wm_image = embed_watermark(pil_image, asset_id, owner_id)
                wm_buf = BytesIO()
                wm_image.save(wm_buf, format="JPEG", quality=95)
                wm_bytes = wm_buf.getvalue()

                wm_path = f"{owner_id}/{asset_id}/watermarked_{filename}"
                await upload_file(wm_bytes, _BUCKET, wm_path)
                watermark_embedded = True
            except Exception as exc:
                logger.warning("Watermark embed failed (non-fatal): %s", exc)

        else:  # video
            clip_vector = extract_video_embedding(tmp_path)
            phash       = extract_video_phash(tmp_path)

    finally:
        os.unlink(tmp_path)

    # ── Step 7: Add to FAISS ────────────────────────────────────────────────
    try:
        faiss_id = await add_asset(clip_vector, asset_id)
    except Exception as exc:
        logger.error("FAISS add_asset failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"FAISS indexing failed: {exc}")

    # ── Step 8: Insert into Supabase ────────────────────────────────────────
    asset_record = {
        "id":          asset_id,
        "owner_id":    owner_id,
        "filename":    filename,
        "media_type":  media_type,
        "storage_url": storage_url,
        "phash":       phash,
        "faiss_id":    faiss_id,
        "title":       title or filename,
    }
    try:
        inserted = await insert_asset(asset_record)
    except Exception as exc:
        logger.error("Supabase insert_asset failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database insert failed: {exc}")

    logger.info("Upload complete: asset_id=%s faiss_id=%d", asset_id, faiss_id)

    return JSONResponse({
        "asset_id":          asset_id,
        "phash":             phash,
        "faiss_id":          faiss_id,
        "storage_url":       storage_url,
        "watermark_embedded": watermark_embedded,
        "media_type":        media_type,
        "title":             title or filename,
    })
