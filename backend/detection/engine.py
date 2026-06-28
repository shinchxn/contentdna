"""
backend/detection/engine.py
────────────────────────────
Central detection engine — the single entry point for ALL infringement checks.

Every detection source (hunter, platform crawlers, manual uploads, URL checks)
calls one of two functions here:
  • detect_from_file(file_bytes, ...)  — when we already have the bytes
  • detect_from_url(url, ...)          — when we have a URL to download

Pipeline (for both):
  1. Fingerprint the suspect media (CLIP embedding + pHash)
  2. Search FAISS for top-20 candidate matches
  3. Compute fusion score (CLIP cosine + pHash Hamming)
  4. Filter: keep only scores ≥ MATCH_THRESHOLD
  5. For images: attempt watermark extraction for cryptographic confirmation
  6. Insert an `alert` row in Supabase for every confirmed match
  7. Return a structured DetectionResult

Design decisions:
  • clip_vector comparison in step 3 uses the FAISS inner-product score as the
    cosine component, which avoids a second CLIP encode. The stored vector was
    L2-normalised at upload time so the inner product == cosine similarity.
  • We store the FAISS inner-product score from step 2 as `clip_score` and
    the asset's stored pHash for the Hamming component, then call compute_score.
  • Watermark extraction is best-effort; a failure does not block the alert.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
from PIL import Image

from backend.config import MATCH_THRESHOLD
from backend.fingerprint.clip_encoder import encode_image
from backend.fingerprint.fusion import compute_score, get_severity
from backend.fingerprint.phash_encoder import encode_phash
from backend.fingerprint.video_processor import (
    extract_video_embedding,
    extract_video_phash,
)
from backend.fingerprint.watermark import extract_watermark
from backend.store.faiss_store import search
from backend.store.supabase_client import get_asset, insert_alert

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DetectionMatch:
    asset_id: str
    owner_id: str
    score: float
    severity: str
    filename: str
    storage_url: str
    watermark_confirmed: bool


@dataclass
class DetectionResult:
    matched: bool
    matches: List[DetectionMatch]
    processing_time_ms: int
    source_url: Optional[str] = None
    page_url: Optional[str] = None
    platform: str = "manual"
    source_type: str = "manual"


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def detect_from_file(
    file_bytes: bytes,
    media_type: str,                    # "image" | "video"
    source_url: Optional[str] = None,
    page_url: Optional[str] = None,
    platform: str = "manual",
    source_type: str = "manual",
) -> DetectionResult:
    """
    Run the full detection pipeline on raw media bytes.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the image or video file.
    media_type : str
        "image" or "video".
    source_url : str | None
        Direct URL of the media file (stored in the alert for evidence).
    page_url : str | None
        Page URL where the media was found (e.g. the Instagram post URL).
    platform : str
        One of: instagram | youtube | tiktok | reddit | web | live | manual
    source_type : str
        One of: hunter | crawler | manual | dorking

    Returns
    -------
    DetectionResult
    """
    start_time = time.time()
    matches: List[DetectionMatch] = []

    # Write to temp file — cv2/PIL need a path, not in-memory bytes
    suffix = ".jpg" if media_type == "image" else ".mp4"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(file_bytes)

        # ── Step 1: Fingerprint ─────────────────────────────────────────────
        if media_type == "image":
            pil_image = Image.open(tmp_path).convert("RGB")
            clip_vector = encode_image(pil_image)
            phash = encode_phash(pil_image)
        else:
            clip_vector = extract_video_embedding(tmp_path)
            phash = extract_video_phash(tmp_path)
            pil_image = None

        # ── Step 2: FAISS search ────────────────────────────────────────────
        candidates = await search(clip_vector, k=20)
        logger.debug("FAISS returned %d candidates", len(candidates))

        # ── Steps 3–6: Score, filter, watermark, insert alert ───────────────
        for asset_id, faiss_score in candidates:
            asset = await get_asset(asset_id)
            if not asset:
                logger.warning("Asset %s not found in Supabase — skipping", asset_id)
                continue

            stored_phash = asset.get("phash") or "0000000000000000"

            # Use FAISS inner-product as cosine component; recompute full fusion
            # score with the stored pHash for the Hamming component.
            # Note: faiss_score is already the cosine similarity (inner product
            # of two unit vectors), so we build a mock call to compute_score
            # that leverages it directly.
            import numpy as np
            # Construct a synthetic second vector whose dot with clip_vector
            # equals faiss_score to cleanly pass through compute_score.
            # Simpler: compute directly inline.
            cosine_clamped = max(0.0, min(1.0, float(faiss_score)))
            from backend.fingerprint.phash_encoder import hamming_distance as _hd
            hamming = _hd(phash, stored_phash)
            phash_score = max(0.0, min(1.0, 1.0 - hamming / 64.0))
            score = round(0.65 * cosine_clamped + 0.35 * phash_score, 4)

            if score < MATCH_THRESHOLD:
                continue

            severity = get_severity(score)
            watermark_confirmed = False

            # ── Step 5: Watermark confirmation ──────────────────────────────
            if pil_image is not None and media_type == "image":
                try:
                    wm = extract_watermark(pil_image)
                    if wm and wm.get("asset_id", "").startswith(asset_id[:8]):
                        watermark_confirmed = True
                except Exception as exc:
                    logger.debug("Watermark extraction error: %s", exc)

            # ── Step 6: Insert alert ─────────────────────────────────────────
            try:
                await insert_alert({
                    "asset_id":            asset_id,
                    "owner_id":            asset["owner_id"],
                    "source_type":         source_type,
                    "platform":            platform,
                    "source_url":          source_url,
                    "page_url":            page_url,
                    "match_score":         score,
                    "severity":            severity,
                    "watermark_confirmed": watermark_confirmed,
                })
            except Exception as exc:
                logger.error("Failed to insert alert for asset %s: %s", asset_id, exc)

            matches.append(DetectionMatch(
                asset_id=asset_id,
                owner_id=asset["owner_id"],
                score=score,
                severity=severity,
                filename=asset.get("filename") or "",
                storage_url=asset.get("storage_url") or "",
                watermark_confirmed=watermark_confirmed,
            ))

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "Detection complete: %d matches in %d ms (platform=%s, source=%s)",
        len(matches), elapsed_ms, platform, source_type,
    )

    return DetectionResult(
        matched=len(matches) > 0,
        matches=sorted(matches, key=lambda m: m.score, reverse=True),
        processing_time_ms=elapsed_ms,
        source_url=source_url,
        page_url=page_url,
        platform=platform,
        source_type=source_type,
    )


async def detect_from_url(
    url: str,
    platform: str = "web",
    page_url: Optional[str] = None,
    source_type: str = "hunter",
) -> DetectionResult:
    """
    Download media from *url* and run detect_from_file on the result.

    Handles images and videos by inspecting the Content-Type header.
    Falls back to "image" if content-type is ambiguous.
    """
    logger.info("Downloading for detection: %s", url)
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "ContentDNA/1.0 (+https://contentdna.io)"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    media_type = "video" if "video" in content_type else "image"

    return await detect_from_file(
        file_bytes=response.content,
        media_type=media_type,
        source_url=url,
        page_url=page_url,
        platform=platform,
        source_type=source_type,
    )
