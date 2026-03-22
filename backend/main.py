"""
main.py — HealBot SaaS API entrypoint.

Run from project root:   python run.py
Run directly:            cd backend && uvicorn main:app --reload --port 8000
"""
from core.batch_scheduler import queue_depth
from core.config import TIER_LIMITS
from api.routers import auth, batches, analytics, stream, intent_maps, heal, sessions
from api.middleware.auth import AuthMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import sys
import os

# ── sys.path fix: MUST be first — before any local imports ───────────────────
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
# ─────────────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="HealBot SaaS API",
    description="AI-powered self-healing test automation as a service",
    version="1.0.0",
)

# ── Middleware (CORS first so it wraps everything, including auth errors) ─────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(batches.router)
app.include_router(analytics.router)
app.include_router(stream.router)
app.include_router(intent_maps.router)
app.include_router(heal.router)        # POST /heal     — SDK inline healing
app.include_router(sessions.router)    # POST /sessions — SDK session lifecycle


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "queue_depth": queue_depth()}


@app.get("/tiers")
def tiers():
    """Tier limits — used by SDK for upgrade prompts."""
    return TIER_LIMITS
