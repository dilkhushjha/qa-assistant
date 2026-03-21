"""
main.py — HealBot SaaS API entrypoint.

Run from project root:   python run.py
Run directly:            cd backend && uvicorn main:app --reload --port 8000
"""
from core.batch_scheduler import queue_depth
from core.config import TIER_LIMITS
from api.routers import auth, batches, analytics, stream, intent_maps
from api.middleware.auth import AuthMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import sys
import os

# ── sys.path fix: must be FIRST before any project imports ───────────────────
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
# ─────────────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="HealBot SaaS API",
    description="AI-powered self-healing test automation as a service",
    version="1.0.0",
)

# ── IMPORTANT: middleware runs in REVERSE order of registration ───────────────
# AuthMiddleware must be added LAST so it runs FIRST (innermost).
# CORSMiddleware must be added FIRST so it runs LAST (outermost) — this ensures
# CORS headers are always present even on 401/4xx responses, so the browser
# doesn't show a CORS error instead of the real auth error.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(auth.router)
app.include_router(batches.router)
app.include_router(analytics.router)
app.include_router(stream.router)
app.include_router(intent_maps.router)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "queue_depth": queue_depth()}


@app.get("/tiers")
def tiers():
    return TIER_LIMITS
