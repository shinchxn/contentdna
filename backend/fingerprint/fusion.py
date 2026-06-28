"""
backend/fingerprint/fusion.py
──────────────────────────────
Combines CLIP cosine similarity + pHash Hamming distance into a single
0.0–1.0 match score, and maps that score to a severity label.

Score formula:
    score = 0.65 × cosine_similarity(clip_a, clip_b)
          + 0.35 × (1 - hamming_distance(phash_a, phash_b) / 64)

Weight rationale:
    CLIP (0.65): dominant signal for semantic matches — same scene from a
                 different camera angle, a TV-screen recording of a broadcast,
                 heavy Instagram filters applied.
    pHash (0.35): secondary signal for near-pixel-identical copies —
                  re-compressed JPEGs, minor crops, slight brightness tweaks.
    The 0.65 / 0.35 split was optimised empirically for sports media detection.
"""

from __future__ import annotations

import numpy as np

from backend.fingerprint.phash_encoder import hamming_distance


def compute_score(
    clip_a: np.ndarray,
    clip_b: np.ndarray,
    phash_a: str,
    phash_b: str,
) -> float:
    """
    Compute a fused similarity score between two media fingerprints.

    Parameters
    ----------
    clip_a, clip_b : np.ndarray
        L2-normalised 512-dim CLIP vectors (as returned by encode_image).
    phash_a, phash_b : str
        16-char hex pHash strings (as returned by encode_phash).

    Returns
    -------
    float
        Fused score in [0.0, 1.0].  Higher = more similar.
        Self-comparison always returns 1.0.
    """
    # Cosine similarity via dot product (valid because vectors are L2-normalised)
    cosine = float(np.dot(clip_a, clip_b))
    cosine = max(0.0, min(1.0, cosine))          # clamp numerical drift

    hamming = hamming_distance(phash_a, phash_b)
    phash_score = 1.0 - (hamming / 64.0)
    phash_score = max(0.0, min(1.0, phash_score))

    raw = 0.65 * cosine + 0.35 * phash_score
    return round(raw, 4)


def get_severity(score: float) -> str:
    """
    Map a fusion score to a human-readable severity label.

    Returns
    -------
    str
        "CRITICAL" | "HIGH" | "MEDIUM" | "NONE"

    Thresholds:
        CRITICAL ≥ 0.95 — near-identical copy (same file, re-uploaded)
        HIGH     ≥ 0.90 — edited repost (filter + crop)
        MEDIUM   ≥ 0.85 — heavily modified but identifiable
        NONE      < 0.85 — below detection threshold
    """
    if score >= 0.95:
        return "CRITICAL"
    elif score >= 0.90:
        return "HIGH"
    elif score >= 0.85:
        return "MEDIUM"
    return "NONE"
