"""
backend/fingerprint/phash_encoder.py
──────────────────────────────────────
Generates a 64-bit perceptual hash (pHash) for images.

Why pHash?
  CLIP captures semantic content; pHash captures pixel-level visual similarity.
  If two images are near-identical visually (same image, different compression
  levels / slight crops) but differ in semantic context, pHash will catch them
  where CLIP might score lower.  Together they give complementary coverage.

Algorithm: DCT-based perceptual hash (imagehash.phash, hash_size=8 → 64 bits).
The output is a hex string that can be stored in Supabase TEXT columns and
compared efficiently with bitwise Hamming distance.
"""

from __future__ import annotations

import imagehash
from PIL import Image


def encode_phash(pil_image: Image.Image) -> str:
    """
    Compute the 64-bit perceptual hash of an image.

    Parameters
    ----------
    pil_image : PIL.Image.Image

    Returns
    -------
    str
        16-character lowercase hex string representing 64 bits of pHash.
        Example: "f8e0c0a0b0d0e0f0"
    """
    hash_obj = imagehash.phash(pil_image, hash_size=8)
    return str(hash_obj)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """
    Compute the Hamming distance between two pHash hex strings.

    Parameters
    ----------
    hash_a, hash_b : str
        16-char hex strings produced by encode_phash().

    Returns
    -------
    int
        0 = identical images, 64 = completely different.
        Typical threshold for "visually similar": ≤ 10.
    """
    h1 = imagehash.hex_to_hash(hash_a)
    h2 = imagehash.hex_to_hash(hash_b)
    return h1 - h2
