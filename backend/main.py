"""
main.py — HealBot SaaS API entrypoint.

Run from ANYWHERE using the launcher at the project root:
    python run.py

Or directly from inside backend/:
    cd backend
    uvicorn main:app --reload --port 8000

Or from the project root:
    uvicorn backend.main:app --reload --port 8000 --app-dir .
"""
# ── sys.path fix ──
from core.batch_scheduler import queue_depth
from core.config import TIER_LIMITS
from api.routers import batches, analytics, stream, intent_maps
from api.middleware.auth import AuthMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os
import sys
import sys as _sys
import os as _os

from api.routers import auth
_BACKEND_DIR = _os.path.abspath(__file__)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)
# ── sys.path fix ──

# ── Path fix — works regardless of CWD or how Python was launched ─────────────

# Add backend/ to sys.path so all flat imports (core.x, healing.x, etc.) resolve
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
# ─────────────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="HealBot SaaS API",
    description="AI-powered self-healing test automation as a service",
    version="1.0.0",
)

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
    """Returns tier limits — useful for SDK upgrade prompts."""
    return TIER_LIMITS
