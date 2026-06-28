"""
backend/hunter/extractors/direct_extractor.py
───────────────────────────────────────────────
Simplest extractor: directly GETs a media URL via httpx and returns a MediaItem.
Used for DIRECT type URLs (.jpg/.mp4/etc. that don't need a browser or
specialised download tool).
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import AsyncGenerator

import httpx

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "ContentDNA/1.0 (+https://contentdna.io)",
    "Accept": "image/*, video/*, */*",
}

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp",
                       "image/avif", "image/heic"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm", "video/quicktime",
                       "video/x-msvideo", "video/x-matroska"}


async def extract_media_direct(url: str) -> AsyncGenerator[MediaItem, None]:
    """
    Download a direct media URL and yield one MediaItem.

    For images: yields with file_bytes populated (no temp file needed).
    For videos:  saves to a temp file and yields with path populated
                 (videos can be large; avoid holding all bytes in memory).

    The caller is responsible for cleaning up any temp files (item.path).
    """
    logger.info("DirectExtractor: fetching %s", url)
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        ct = response.headers.get("content-type", "").split(";")[0].strip().lower()

        if ct in IMAGE_CONTENT_TYPES or ct.startswith("image/"):
            yield MediaItem(
                url=url,
                path=None,
                page_url=url,
                media_type="image",
                file_bytes=response.content,
            )

        elif ct in VIDEO_CONTENT_TYPES or ct.startswith("video/"):
            # Save to temp file
            suffix = _ext_from_ct(ct) or ".mp4"
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(response.content)
                yield MediaItem(
                    url=url,
                    path=tmp_path,
                    page_url=url,
                    media_type="video",
                )
            except Exception:
                os.unlink(tmp_path)
                raise

        else:
            # Try to sniff from URL extension
            url_lower = url.lower().split("?")[0]
            if any(url_lower.endswith(ext) for ext in
                   [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                yield MediaItem(
                    url=url,
                    path=None,
                    page_url=url,
                    media_type="image",
                    file_bytes=response.content,
                )
            elif any(url_lower.endswith(ext) for ext in
                     [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
                suffix = os.path.splitext(url_lower)[1] or ".mp4"
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(response.content)
                yield MediaItem(
                    url=url,
                    path=tmp_path,
                    page_url=url,
                    media_type="video",
                )
            else:
                logger.debug("DirectExtractor: unrecognised content-type %s for %s", ct, url)

    except httpx.HTTPStatusError as exc:
        logger.warning("DirectExtractor HTTP error %d for %s", exc.response.status_code, url)
    except Exception as exc:
        logger.error("DirectExtractor error for %s: %s", url, exc)


def _ext_from_ct(content_type: str) -> str:
    mapping = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/x-matroska": ".mkv",
    }
    return mapping.get(content_type, ".mp4")
