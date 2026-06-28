"""
backend/fingerprint/video_processor.py

Source: project/reference/fingerprint/ → concept: frame sampling
Modified: replaced old hashing with CLIP mean pooling from clip_encoder
"""
import cv2
import numpy as np
from PIL import Image
from backend.fingerprint.clip_encoder import encode_image
from backend.fingerprint.phash_encoder import encode_phash


def extract_video_embedding(video_path: str) -> np.ndarray:
    """Sample 1 frame per second, CLIP-encode each, return mean-pooled vector."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval = int(fps)
    embeddings, count = [], 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            embeddings.append(encode_image(pil))
        count += 1
    cap.release()
    if not embeddings:
        return np.zeros(512, dtype=np.float32)
    mean = np.mean(embeddings, axis=0).astype(np.float32)
    norm = np.linalg.norm(mean)
    return mean / norm if norm > 0 else mean


def extract_video_phash(video_path: str) -> str:
    """Extract pHash from the middle frame of the video."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return "0000000000000000"
    return encode_phash(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
