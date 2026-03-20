"""
config.py — Single source of truth for all HealBot SaaS configuration.
All values can be overridden via environment variables.
"""
import os

# ── Database ──────────────────────────────────────────────────────────────────
DB_URL = os.environ.get("HEALBOT_DB_URL", "sqlite:///./data/healbot_saas.db")

# ── Queue / Workers ───────────────────────────────────────────────────────────
MAX_WORKERS = int(os.environ.get("HEALBOT_WORKERS",    8))
MAX_QUEUED = int(os.environ.get("HEALBOT_MAX_QUEUED", 200))
SCRIPT_TIMEOUT = int(os.environ.get(
    "HEALBOT_SCRIPT_TIMEOUT", 300))  # seconds per script

# ── Healing ───────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = int(os.environ.get("HEALBOT_CONFIDENCE", 3))
OLLAMA_URL = os.environ.get(
    "OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
LLAVA_MODEL = os.environ.get("LLAVA_MODEL",  "llava")
LLM_TIMEOUT = int(os.environ.get("HEALBOT_LLM_TIMEOUT", 60))

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("HEALBOT_JWT_SECRET", "change-me-in-production")
JWT_ALGO = "HS256"
JWT_EXPIRE_H = int(os.environ.get("HEALBOT_JWT_EXPIRE_H", 24))

# ── Tiers ─────────────────────────────────────────────────────────────────────
TIER_LIMITS = {
    "free":       {"scripts_per_day": 10,   "workers": 1, "history_days": 7},
    "starter":    {"scripts_per_day": 100,  "workers": 2, "history_days": 30},
    "pro":        {"scripts_per_day": 1000, "workers": 4, "history_days": 90},
    "enterprise": {"scripts_per_day": -1,   "workers": 8, "history_days": -1},
}

# ── Paths ─────────────────────────────────────────────────────────────────────
ARTIFACTS_ROOT = os.environ.get("HEALBOT_ARTIFACTS", "./artifacts")
MEMORY_ROOT = os.environ.get("HEALBOT_MEMORY",    "./memory")
GLOBAL_MEMORY = os.path.join(MEMORY_ROOT, "global_memory.json")
