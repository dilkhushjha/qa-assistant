"""
learning_engine.py — Per-tenant healed selector memory.

Each tenant gets their own memory file: memory/<tenant_id>.json
A shared global pool (memory/global.json) accumulates anonymised patterns
from all tenants — so a selector healed by one tenant benefits others.

Cross-run learning: every successful heal is written to both files.
On recall, tenant file is checked first, then global pool.
"""

import json
import os
import threading
from core.logger import log
from core.config import MEMORY_ROOT

_lock = threading.Lock()
os.makedirs(MEMORY_ROOT, exist_ok=True)

GLOBAL_MEMORY = os.path.join(MEMORY_ROOT, "global.json")


def _path(tenant_id: str) -> str:
    return os.path.join(MEMORY_ROOT, f"{tenant_id}.json")


def _read(path: str) -> dict:
    try:
        return json.loads(open(path).read()) if os.path.exists(path) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def _write(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def learn(old: str, new: str, tenant_id: str = "default", ctx=None):
    """Store old→new in both the tenant file and the global pool."""
    with _lock:
        # Tenant memory
        t_path = _path(tenant_id)
        t_data = _read(t_path)
        t_data[old] = new
        _write(t_path, t_data)

        # Global pool (anonymised — selector only, no tenant info)
        g_data = _read(GLOBAL_MEMORY)
        # Only write to global if not already known — first writer wins
        if old not in g_data:
            g_data[old] = new
            _write(GLOBAL_MEMORY, g_data)

    log("MEMORY", f"Stored [{tenant_id}]: {old[:40]} → {new[:40]}", ctx=ctx)


def recall(selector: str, tenant_id: str = "default") -> str | None:
    """Check tenant memory first, then global pool."""
    with _lock:
        # 1. Tenant-specific memory
        t_data = _read(_path(tenant_id))
        if selector in t_data:
            return t_data[selector]

        # 2. Global pool (cross-tenant learning)
        g_data = _read(GLOBAL_MEMORY)
        return g_data.get(selector)
