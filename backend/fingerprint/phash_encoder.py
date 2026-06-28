"""
backend/fingerprint/phash_encoder.py

Copied from: project/fingerprint/imagehash/imagehash/__init__.py
  - Copied: phash() function → converted to wrapper
  - Copied: hex_to_hash() function → used for Hamming subtraction
  - Modified: wrapped into two ContentDNA-specific functions only
"""
# Source: project/fingerprint/imagehash/imagehash/__init__.py
# Copyright (c) 2013-2022, Johannes Buchner — BSD License
import imagehash
from PIL import Image


def encode_phash(pil_image: Image.Image) -> str:
    # Calls imagehash.phash() from project/fingerprint/imagehash/
    # hash_size=8 → 8x8 DCT grid → 64-bit hash → 16 hex chars
    return str(imagehash.phash(pil_image, hash_size=8))


def hamming_distance(hash_a: str, hash_b: str) -> int:
    # Uses ImageHash.__sub__ which calls numpy.count_nonzero(a.hash != b.hash)
    # Returns int in range [0, 64]
    return imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)
