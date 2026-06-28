"""
backend/hunter/extractors/streamlink_extractor.py
───────────────────────────────────────────────────
Extracts media from live streams using streamlink.

Strategy:
  1. Open the best available quality stream.
  2. Read the first ~10 seconds of stream data into a temp .ts file.
  3. Extract 3 keyframes with OpenCV (start, middle, end of the 10s window).
  4. Yield each keyframe as an image MediaItem.

  This gives a representative visual fingerprint of the live broadcast
  that can be compared against registered broadcast assets.

Why only 10 seconds?
  Live stream detection is best done frequently and cheaply.  A 10-second
  sample is sufficient for CLIP to identify the broadcast scene.
  The hunt_job can call this repeatedly on a rolling basis.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import AsyncGenerator, List

import cv2
import numpy as np

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

_SAMPLE_DURATION = 10       # seconds of stream to capture
_KEYFRAMES_COUNT = 3        # keyframes to extract


def _capture_stream(url: str, output_path: str, duration_sec: int = 10) -> bool:
    """
    Open the best quality stream at *url* via streamlink and write
    *duration_sec* seconds to *output_path*.  Returns True on success.
    """
    try:
        import streamlink

        sl = streamlink.Streamlink()
        streams = sl.streams(url)
        if not streams:
            logger.warning("Streamlink: no streams found for %s", url)
            return False

        # Pick quality: best → 720p → 480p → worst
        quality = next(
            (q for q in ["best", "720p", "480p", "worst"] if q in streams),
            None,
        )
        if quality is None:
            quality = list(streams.keys())[0]

        stream = streams[quality]
        fd = stream.open()

        bytes_per_sec_estimate = 500 * 1024   # 500 KB/s estimate for safety
        total_bytes = bytes_per_sec_estimate * duration_sec
        data = b""
        while len(data) < total_bytes:
            chunk = fd.read(65536)
            if not chunk:
                break
            data += chunk
        fd.close()

        with open(output_path, "wb") as f:
            f.write(data)

        return os.path.getsize(output_path) > 1024

    except Exception as exc:
        logger.error("Streamlink capture error for %s: %s", url, exc)
        return False


def _extract_keyframes(video_path: str, n: int = 3) -> List[np.ndarray]:
    """Extract *n* evenly-spaced frames from a video file as BGR numpy arrays."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: List[np.ndarray] = []

    if total <= 0:
        cap.release()
        return frames

    indices = [int(i * total / n) for i in range(n)]
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames


async def extract_media_streamlink(url: str) -> AsyncGenerator[MediaItem, None]:
    """
    Capture a live stream and yield keyframe images.

    Yields
    ------
    MediaItem (media_type="image")
        One item per keyframe extracted from the stream capture.
    """
    logger.info("StreamlinkExtractor: capturing from %s", url)
    loop = asyncio.get_event_loop()

    tmp_dir = tempfile.mkdtemp(prefix="contentdna_streamlink_")
    ts_path  = os.path.join(tmp_dir, "capture.ts")

    success = await loop.run_in_executor(
        None, _capture_stream, url, ts_path, _SAMPLE_DURATION
    )
    if not success:
        logger.warning("StreamlinkExtractor: capture failed for %s", url)
        return

    # Extract keyframes on executor (cv2 is CPU-bound)
    frames = await loop.run_in_executor(
        None, _extract_keyframes, ts_path, _KEYFRAMES_COUNT
    )
    logger.debug("StreamlinkExtractor: extracted %d keyframes", len(frames))

    for i, frame_bgr in enumerate(frames):
        frame_path = os.path.join(tmp_dir, f"frame_{i}.jpg")
        cv2.imwrite(frame_path, frame_bgr)
        yield MediaItem(
            url=url,
            path=frame_path,
            page_url=url,
            media_type="image",
        )
