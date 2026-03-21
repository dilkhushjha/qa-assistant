"""
run.py — HealBot SaaS launcher.
Place this file at your project root (same level as backend/).

Usage:
    python run.py               # start server on port 8000
    python run.py --port 8080
    python run.py --reload      # dev mode, auto-reloads on file changes
    python run.py --headless    # no Chrome window (CI mode)
"""
import uvicorn
import sys
import os
import argparse

# ── Resolve backend/ directory ────────────────────────────────────────────────
# __file__ is project_root/run.py  →  backend/ is alongside it
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if not os.path.isdir(BACKEND_DIR):
    print(f"ERROR: backend/ not found at {BACKEND_DIR}")
    print("Make sure run.py is in the same folder as backend/")
    sys.exit(1)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="HealBot SaaS API server")
parser.add_argument("--host",     default="0.0.0.0",
                    help="Bind host (default: 0.0.0.0)")
parser.add_argument("--port",     default=8000, type=int,
                    help="Port (default: 8000)")
parser.add_argument("--reload",   action="store_true",
                    help="Auto-reload on code changes")
parser.add_argument("--workers",  default=1, type=int,
                    help="Uvicorn workers (default: 1)")
parser.add_argument("--headless", action="store_true",
                    help="Run Chrome headless (CI)")
args = parser.parse_args()

if args.headless:
    os.environ["HEALBOT_HEADLESS"] = "1"

print(f"""
╔══════════════════════════════════════════════════╗
║  HealBot SaaS                                    ║
╠══════════════════════════════════════════════════╣
║  API   →  http://localhost:{args.port}           ║
║  Docs  →  http://localhost:{args.port}/docs      ║
║  Mode  →  {'reload (dev)' if args.reload else 'production'}                           ║
╚══════════════════════════════════════════════════╝
""")

# relative paths (data/, memory/, artifacts/) resolve correctly
os.chdir(BACKEND_DIR)
uvicorn.run(
    "main:app",
    host=args.host,
    port=args.port,
    reload=args.reload,
    workers=args.workers if not args.reload else 1,
    log_level="info",
)
