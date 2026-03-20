"""
run.py — HealBot SaaS launcher.

Run from ANYWHERE:
    python run.py
    python run.py --port 8080
    python run.py --reload        (dev mode)
    python run.py --headless      (CI mode — no browser window)

This script adds backend/ to sys.path then starts uvicorn.
You never need to cd anywhere or set PYTHONPATH.
"""

import uvicorn
import sys
import os
import argparse

# ── Resolve paths ──────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if not os.path.isdir(BACKEND_DIR):
    print(f"ERROR: backend/ directory not found at {BACKEND_DIR}")
    sys.exit(1)

# Put backend/ on sys.path so all flat imports resolve
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Args ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="HealBot SaaS API server")
parser.add_argument("--host",     default="0.0.0.0",
                    help="Bind host (default: 0.0.0.0)")
parser.add_argument("--port",     default=8000, type=int,
                    help="Port (default: 8000)")
parser.add_argument("--reload",   action="store_true",
                    help="Auto-reload on code changes (dev)")
parser.add_argument("--workers",  default=1, type=int,
                    help="Uvicorn workers (default: 1)")
parser.add_argument("--headless", action="store_true",
                    help="Run Chrome headless (CI mode)")
args = parser.parse_args()

if args.headless:
    os.environ["HEALBOT_HEADLESS"] = "1"

# ── Start ──────────────────────────────────────────────────────────────────────
print(f"""
╔══════════════════════════════════════════════════╗
║  HealBot SaaS                                    ║
╠══════════════════════════════════════════════════╣
║  API   →  http://{args.host}:{args.port}         ║
║  Docs  →  http://localhost:{args.port}/docs      ║
║  Mode  →  {'reload (dev)' if args.reload else 'production'}                           ║
╚══════════════════════════════════════════════════╝
""")


# Change to backend dir so relative paths (data/, memory/, artifacts/) resolve correctly
os.chdir(BACKEND_DIR)

uvicorn.run(
    "main:app",
    host=args.host,
    port=args.port,
    reload=args.reload,
    workers=args.workers if not args.reload else 1,
    log_level="info",
)
