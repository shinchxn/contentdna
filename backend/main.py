"""
backend/main.py — ContentDNA API entry point.
Exactly as specified in the build spec (File 19).
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from backend.fingerprint.clip_encoder import load_model
from backend.store.faiss_store import _load as load_faiss
from backend.store.supabase_client import get_client
from backend.routers import upload, detect, check_url, hunt, alerts, assets, stats, discover

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# WebSocket set (spec: connected_ws = set())
connected_ws = set()


@asynccontextmanager
async def lifespan(app):
    load_model()
    load_faiss()
    get_client()
    yield


app = FastAPI(title="ContentDNA API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(detect.router)
app.include_router(check_url.router)
app.include_router(hunt.router)
app.include_router(alerts.router)
app.include_router(assets.router)
app.include_router(stats.router)
app.include_router(discover.router)


@app.get("/health", tags=["system"])
async def health():
    from backend.store.faiss_store import index_size
    return {"status": "ok", "faiss_size": index_size(), "ws_clients": len(connected_ws)}


# Spec: WebSocket /ws/alerts
@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    connected_ws.add(websocket)
    try:
        while True:
            await asyncio.sleep(30)
    except (WebSocketDisconnect, Exception):
        connected_ws.discard(websocket)


async def broadcast(alert: dict):
    """Broadcast a new alert to all connected WS clients."""
    dead = set()
    for ws in connected_ws:
        try:
            await ws.send_json({"type": "new_alert", "alert": alert})
        except Exception:
            dead.add(ws)
    connected_ws -= dead
