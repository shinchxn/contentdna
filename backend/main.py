"""
backend/main.py
────────────────
FastAPI application entry point.

Startup sequence (lifespan):
  1. Load CLIP model into memory (once, ~3s)
  2. Load FAISS index from disk (once)
  3. Validate Supabase connectivity

Routes:
  POST  /upload            — Register new asset
  POST  /detect            — Manual file detection
  POST  /check-url         — URL-based detection
  POST  /hunt              — Start background hunt job
  GET   /hunt/status/{id}  — Poll hunt job progress
  GET   /alerts            — Paginated alert list
  GET   /alerts/{id}       — Single alert detail
  GET   /stats             — Dashboard statistics
  WS    /ws/alerts         — WebSocket for real-time alert push

Celery worker (separate process):
  celery -A backend.crawlers.worker worker -c 4
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.fingerprint.clip_encoder import load_model
from backend.store.faiss_store import _load_or_create
from backend.routers import alerts, check_url, detect, hunt, stats, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        logger.info("WS client connected (total: %d)", len(self._clients))

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        logger.info("WS client disconnected (total: %d)", len(self._clients))

    async def broadcast(self, message: dict) -> None:
        dead: set[WebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._clients -= dead


manager = ConnectionManager()


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("=== ContentDNA API starting ===")

    logger.info("Loading CLIP model (openai/clip-vit-large-patch14)…")
    load_model()
    logger.info("CLIP model ready.")

    logger.info("Loading FAISS index…")
    _load_or_create()
    logger.info("FAISS index ready.")

    logger.info("Supabase will connect on first request.")
    logger.info("=== ContentDNA API ready — http://localhost:8000/docs ===")

    yield  # ← app serves requests here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("ContentDNA API shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ContentDNA API",
    description=(
        "AI-powered digital media rights enforcement.\n\n"
        "Detects stolen sports media across Instagram, YouTube, TikTok, "
        "Reddit, and any website using CLIP semantic embeddings + pHash fusion."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server (Person 2 frontend)
        "http://localhost:3000",    # Next.js fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(upload.router)
app.include_router(detect.router)
app.include_router(check_url.router)
app.include_router(hunt.router)
app.include_router(alerts.router)
app.include_router(stats.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health():
    from backend.store.faiss_store import index_size
    return {
        "status":      "ok",
        "faiss_size":  index_size(),
        "ws_clients":  len(manager._clients),
    }


# ── WebSocket — real-time alert push ─────────────────────────────────────────

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Real-time alert push endpoint.
    Frontend subscribes here; detection engine calls broadcast_alert() to push.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive — client sends pings, we just wait
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


async def broadcast_alert(alert: dict) -> None:
    """
    Broadcast a new alert to all connected WebSocket clients.
    Call this from detection engine or Celery task after inserting an alert.
    """
    await manager.broadcast({"type": "new_alert", "alert": alert})
