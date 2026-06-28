"""
backend/hunter/media_item.py
──────────────────────────────
Shared data class representing a single piece of media discovered during a hunt.
Used by all 6 extractors and consumed by the hunt_job runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MediaItem:
    """
    Represents a single media item discovered during a hunt.

    Attributes
    ----------
    url : str | None
        Remote URL to download from.  Set when the media has not yet been
        downloaded locally.
    path : str | None
        Local filesystem path.  Set when the extractor has already downloaded
        the file (e.g. gallery-dl, yt-dlp, streamlink extractors).
    page_url : str | None
        The page URL where this media was found (for evidence / alert record).
    media_type : str
        "image" or "video".
    file_bytes : bytes | None
        In-memory bytes when the extractor has already fetched the content
        (e.g. direct_extractor for small images).
    """

    url: Optional[str]
    path: Optional[str]
    page_url: Optional[str]
    media_type: str                    # "image" | "video"
    file_bytes: Optional[bytes] = field(default=None, repr=False)

    def has_content(self) -> bool:
        """True if we already have the media bytes or a local path."""
        return self.path is not None or self.file_bytes is not None
