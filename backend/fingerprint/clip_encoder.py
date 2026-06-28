"""
backend/fingerprint/clip_encoder.py
─────────────────────────────────────
Generates a 512-dimensional semantic embedding for any image using OpenAI CLIP
(openai/clip-vit-large-patch14).

Why CLIP?
  CLIP understands image *content* — not just pixels.  A photograph of a
  football goal looks nearly identical whether it's been JPEG-compressed,
  cropped, resized, or reposted to Instagram.  The semantic embedding stays
  stable across all these transforms, which is exactly what we need for
  rights-infringement detection.

Key design decision:
  The model is loaded ONCE at module import (lazy on first call).
  Never reload per-request — the model is ~900 MB and takes ~3 s to load.
  All inference is done with torch.no_grad() for speed.
  Output is L2-normalised so cosine similarity = dot product (FAISS IndexFlatIP).
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

logger = logging.getLogger(__name__)

MODEL_NAME = "openai/clip-vit-large-patch14"

_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None


def load_model() -> Tuple[CLIPModel, CLIPProcessor]:
    """
    Lazy-load the CLIP model and processor.
    Thread-safe in the sense that FastAPI runs in a single process with
    asyncio — the startup hook calls this before any requests are served.
    """
    global _model, _processor
    if _model is None:
        logger.info("Loading CLIP model: %s", MODEL_NAME)
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()

        # Move to GPU if available, stay on CPU otherwise
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(device)
        logger.info("CLIP model loaded on %s", device)

    return _model, _processor  # type: ignore[return-value]


def encode_image(pil_image: Image.Image) -> np.ndarray:
    """
    Encode a PIL image into a 512-dimensional L2-normalised float32 vector.

    Parameters
    ----------
    pil_image : PIL.Image.Image
        Any size, any mode.  Will be converted to RGB internally by the
        CLIP processor.

    Returns
    -------
    np.ndarray
        Shape (512,), dtype float32, L2 norm ≈ 1.0.

    Notes
    -----
    L2 normalisation is critical: FAISS IndexFlatIP computes inner products,
    which equal cosine similarity when both vectors are unit-length.
    """
    model, processor = load_model()
    device = next(model.parameters()).device

    # The CLIP processor handles resizing + normalisation for us
    inputs = processor(images=pil_image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        features = model.get_image_features(**inputs)

    # Move back to CPU, squeeze batch dimension
    vector = features.squeeze(0).cpu().numpy().astype(np.float32)

    # L2 normalise
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector
