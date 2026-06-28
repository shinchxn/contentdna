"""
backend/store/faiss_store.py
──────────────────────────────
Thread-safe (asyncio-safe) FAISS vector index for asset embeddings.

Architecture:
  - IndexFlatIP (flat inner-product index): exact search, no approximation.
    Works well up to ~1 million vectors on CPU.  For larger deployments
    switch to IndexIVFFlat with nprobe tuning.
  - The index is persisted to FAISS_INDEX_PATH (.bin file).
  - A companion JSON map ({faiss_id → asset_id}) lives alongside it so we can
    translate FAISS row indices back to Supabase UUIDs.
  - An asyncio.Lock guards all mutations to prevent concurrent write corruption.
  - On module import _load_or_create() runs synchronously (before any async
    code) to warm up the index.

Scaling note:
  When ntotal > 500k, replace IndexFlatIP with:
      faiss.IndexIVFFlat(quantiser, 512, 2048, faiss.METRIC_INNER_PRODUCT)
  and train it on a representative sample.  For now, flat is simpler and
  perfectly fast for the expected scale.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np

from backend.config import FAISS_INDEX_PATH

logger = logging.getLogger(__name__)

_index: Optional[faiss.Index] = None
_id_map: Dict[int, str] = {}           # faiss row index → Supabase asset UUID
_lock = asyncio.Lock()
_map_path: str = FAISS_INDEX_PATH.replace(".bin", "_map.json")


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load() -> None:
    """Load existing index from disk, or create a fresh one."""
    global _index, _id_map

    if os.path.exists(FAISS_INDEX_PATH):
        logger.info("Loading FAISS index from %s", FAISS_INDEX_PATH)
        _index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info("FAISS index loaded: %d vectors", _index.ntotal)
    else:
        logger.info("Creating new FAISS IndexFlatIP(512)")
        _index = faiss.IndexFlatIP(512)   # 512-dim inner product

    if os.path.exists(_map_path):
        with open(_map_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _id_map = {int(k): v for k, v in raw.items()}
        logger.info("Loaded %d id-map entries from %s", len(_id_map), _map_path)


def _save() -> None:
    """Persist index and id-map to disk. Call only while holding _lock."""
    os.makedirs(os.path.dirname(os.path.abspath(FAISS_INDEX_PATH)), exist_ok=True)
    faiss.write_index(_index, FAISS_INDEX_PATH)
    with open(_map_path, "w", encoding="utf-8") as f:
        json.dump(_id_map, f)


# ── Public async API ─────────────────────────────────────────────────────────

async def add_asset(clip_vector: np.ndarray, asset_id: str) -> int:
    """
    Add a new L2-normalised CLIP vector to the index.

    Parameters
    ----------
    clip_vector : np.ndarray
        Shape (512,) or (1, 512), dtype float32, L2-normalised.
    asset_id : str
        Supabase UUID for this asset.

    Returns
    -------
    int
        The FAISS row index (faiss_id) assigned to this vector.
    """
    async with _lock:
        if _index is None:
            _load()

        vec = clip_vector.reshape(1, 512).astype(np.float32)
        _index.add(vec)                     # type: ignore[union-attr]
        faiss_id = _index.ntotal - 1        # type: ignore[union-attr]
        _id_map[faiss_id] = asset_id
        _save()
        logger.debug("Added asset %s → faiss_id %d", asset_id, faiss_id)
        return faiss_id


async def search(
    clip_vector: np.ndarray,
    k: int = 20,
) -> List[Tuple[str, float]]:
    """
    Find the *k* most similar vectors in the index.

    Parameters
    ----------
    clip_vector : np.ndarray
        Shape (512,), L2-normalised query vector.
    k : int
        Number of candidates to return (capped at index size).

    Returns
    -------
    list of (asset_id, score) tuples
        Sorted by score descending.  Score ∈ [0, 1] (inner product of unit
        vectors = cosine similarity).
    """
    async with _lock:
        if _index is None:
            _load()

        if _index.ntotal == 0:              # type: ignore[union-attr]
            return []

        vec = clip_vector.reshape(1, 512).astype(np.float32)
        k   = min(k, _index.ntotal)        # type: ignore[union-attr]

        scores_arr, indices_arr = _index.search(vec, k)  # type: ignore[union-attr]

        results: List[Tuple[str, float]] = []
        for idx, score in zip(indices_arr[0], scores_arr[0]):
            idx = int(idx)
            if idx >= 0 and idx in _id_map:
                results.append((_id_map[idx], float(score)))

        return sorted(results, key=lambda x: x[1], reverse=True)


def get_asset_id(faiss_id: int) -> Optional[str]:
    """Synchronous lookup: faiss_id → asset UUID."""
    return _id_map.get(faiss_id)


def index_size() -> int:
    """Return the number of vectors currently in the index."""
    if _index is None:
        return 0
    return _index.ntotal  # type: ignore[union-attr]


# ── Warm up on module import ─────────────────────────────────────────────────
_load()
