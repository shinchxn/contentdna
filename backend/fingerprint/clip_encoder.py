"""
backend/fingerprint/clip_encoder.py

No existing repo to copy from — written directly using HuggingFace transformers.
Uses openai/clip-vit-large-patch14 for 512-dim semantic embeddings.
"""
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
import torch

_model, _processor = None, None


def load_model():
    global _model, _processor
    if _model is None:
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()


def encode_image(pil_image: Image.Image) -> np.ndarray:
    load_model()
    inputs = _processor(images=pil_image, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    with torch.no_grad():
        vision_outputs = _model.vision_model(**inputs)
        pooled_output = vision_outputs[1]
        features = _model.visual_projection(pooled_output)
    vec = features.squeeze().cpu().numpy().astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec
