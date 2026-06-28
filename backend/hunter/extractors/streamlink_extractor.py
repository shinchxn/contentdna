"""
backend/hunter/extractors/streamlink_extractor.py

Source: project/hunter/streamlink_engine/src/streamlink/api.py
  - Copied: session = Streamlink(); session.streams(url) pattern
  - From api.py line 14-16: session = Streamlink(); return session.streams(url, **params)
  - Modified: open best stream, read 10MB (~10 seconds), extract keyframes with OpenCV
"""
import asyncio
import logging
import os
import tempfile
import cv2
import numpy as np
from PIL import Image
from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 10 * 1024 * 1024   # 10 MB ≈ 10 seconds at 720p


def _capture_stream_sync(url: str, out_path: str) -> bool:
    """
    Copied pattern from streamlink/api.py:
      session = Streamlink()
      streams = session.streams(url)

    Modified: pick best quality, read ~10MB, save to file.
    """
    try:
        from streamlink.session import Streamlink
        session = Streamlink()
        streams = session.streams(url)
        if not streams:
            return False

        quality = next(
            (q for q in ["best", "720p", "480p", "worst"] if q in streams),
            list(streams.keys())[0] if streams else None,
        )
        if not quality:
            return False

        fd = streams[quality].open()
        data = b""
        while len(data) < _CHUNK_SIZE:
            chunk = fd.read(65536)
            if not chunk:
                break
            data += chunk
        fd.close()

        with open(out_path, "wb") as f:
            f.write(data)
        return os.path.getsize(out_path) > 1024
    except Exception as exc:
        logger.error("streamlink error for %s: %s", url, exc)
        return False


def _extract_keyframes_sync(video_path: str, n: int = 3) -> list:
    """Extract n evenly-spaced frames from video as PIL Images."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total <= 0:
        cap.release()
        return frames
    for idx in [int(i * total / n) for i in range(n)]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    cap.release()
    return frames


async def extract_media_streamlink(url: str):
    loop = asyncio.get_event_loop()
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_streamlink_")
    ts_path = os.path.join(tmp_dir, "capture.ts")

    success = await loop.run_in_executor(None, _capture_stream_sync, url, ts_path)
    if not success:
        return

    frames = await loop.run_in_executor(None, _extract_keyframes_sync, ts_path, 3)
    for i, pil_frame in enumerate(frames):
        frame_path = os.path.join(tmp_dir, f"frame_{i}.jpg")
        pil_frame.save(frame_path, "JPEG")
        yield MediaItem(url=url, path=frame_path, page_url=url, media_type="image")
