"""
backend/config.py
─────────────────
Single source of truth for all environment-backed configuration.
Loaded once at import time via python-dotenv.
Never hardcode any value here — everything comes from .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Copy .env.example to .env and fill in the value."
        )
    return val

def _optional_str(name: str, default: str) -> str:
    return os.getenv(name, default)

def _optional_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default

def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str           = _require("SUPABASE_URL")
SUPABASE_ANON_KEY: str      = _require("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY: str   = _require("SUPABASE_SERVICE_KEY")

# ── Platform API Keys ─────────────────────────────────────────────────────────
YOUTUBE_API_KEY: str        = _optional_str("YOUTUBE_API_KEY", "")
BING_SEARCH_API_KEY: str    = _optional_str("BING_SEARCH_API_KEY", "")

# ── Infrastructure ────────────────────────────────────────────────────────────
REDIS_URL: str              = _optional_str("REDIS_URL", "redis://localhost:6379/0")

# ── ContentDNA Config ─────────────────────────────────────────────────────────
FAISS_INDEX_PATH: str       = _optional_str("FAISS_INDEX_PATH", "./data/faiss_index.bin")
MATCH_THRESHOLD: float      = _optional_float("MATCH_THRESHOLD", 0.85)
HUNTER_MAX_DEPTH: int       = _optional_int("HUNTER_MAX_DEPTH", 3)
HUNTER_MAX_PAGES: int       = _optional_int("HUNTER_MAX_PAGES", 100)
CONTENTDNA_API_URL: str     = _optional_str("CONTENTDNA_API_URL", "http://localhost:8000")
