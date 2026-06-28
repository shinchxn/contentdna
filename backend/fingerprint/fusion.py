"""
backend/fingerprint/fusion.py

Core ContentDNA innovation formula — no repo to copy from.
Combines CLIP cosine similarity (0.65) with pHash Hamming similarity (0.35).
"""
import numpy as np
from backend.fingerprint.phash_encoder import hamming_distance


def compute_score(clip_a, clip_b, phash_a: str, phash_b: str) -> float:
    """
    Fuse CLIP cosine similarity and pHash Hamming similarity.

    clip_a, clip_b: L2-normalised float32 vectors of dim 512
    phash_a, phash_b: 16-char hex strings from encode_phash()

    Returns a float in [0, 1] where 1.0 = identical.
    """
    cosine = float(np.dot(clip_a, clip_b))
    cosine = max(0.0, min(1.0, cosine))

    phash_score = 1.0 - (hamming_distance(phash_a, phash_b) / 64.0)
    phash_score = max(0.0, min(1.0, phash_score))

    return round(0.65 * cosine + 0.35 * phash_score, 4)


def get_severity(score: float) -> str:
    if score >= 0.95: return "CRITICAL"
    if score >= 0.90: return "HIGH"
    if score >= 0.85: return "MEDIUM"
    return "NONE"
