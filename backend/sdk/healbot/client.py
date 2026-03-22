"""
healbot/client.py — Universal HealBot Client

Usage (any framework):
    from healbot import HealBot
    hb = HealBot(api_key="hb_live_...", url="http://localhost:8000")
    hb.activate()     # auto-detects + patches the current framework
    # ... run your tests ...
    hb.deactivate()

Or zero-config with pytest:
    pip install healbot-sdk
    set HEALBOT_API_KEY=hb_live_...
    pytest
"""

import os
import json
import threading
import urllib.request
import urllib.error
from datetime import datetime


class HealBot:
    def __init__(self, api_key: str = "", url: str = "http://localhost:8000", verbose: bool = True):
        self.api_key = api_key or os.environ.get("HEALBOT_API_KEY", "")
        self.url = (url or os.environ.get("HEALBOT_URL",
                    "http://localhost:8000")).rstrip("/")
        self.verbose = verbose

        self._session_id: str | None = None
        self._run_id:     str | None = None   # the script_run id for SSE streaming
        self._batch_id:   str | None = None
        self._adapter = None
        self._lock = threading.Lock()
        self._heals:    list = []
        self._failures: list = []

        if not self.api_key:
            self._warn("No API key — set HEALBOT_API_KEY or pass api_key=")

    # ── Connection ─────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return True
        except Exception:
            return False

    # ── Session lifecycle ──────────────────────────────────────────────────────

    def start_session(self, name: str = "", framework: str = "unknown") -> str:
        resp = self._post("/sessions/start",
                          {"name": name, "framework": framework})
        if not resp:
            return ""

        self._session_id = resp.get("session_id", "")
        self._run_id = resp.get("run_id", "")
        self._batch_id = resp.get("batch_id", "")
        self._heals = []
        self._failures = []

        stream_url = resp.get("stream_url", "")
        self._log(
            f"Session started — id={self._session_id} | "
            f"Dashboard: {self.url}/stream/{self._run_id}"
        )
        return self._session_id

    def end_session(self) -> dict:
        if not self._session_id:
            return {}
        resp = self._post("/sessions/end", {"session_id": self._session_id})
        self._log(
            f"Session ended — healed={resp.get('healed', 0)} "
            f"failed={resp.get('failed', 0)} "
            f"heal_rate={resp.get('heal_rate', 0)}%"
        )
        self._session_id = None
        self._run_id = None
        self._batch_id = None
        return resp

    def session_report(self) -> dict:
        with self._lock:
            total = len(self._heals) + len(self._failures)
            return {
                "session_id":     self._session_id,
                "run_id":         self._run_id,
                "batch_id":       self._batch_id,
                "total_heals":    len(self._heals),
                "total_failures": len(self._failures),
                "heal_rate":      round(len(self._heals) / total * 100, 1) if total else 0,
                "heals":          list(self._heals),
                "failures":       list(self._failures),
            }

    # ── Core heal ──────────────────────────────────────────────────────────────

    def heal(self, selector: str, html: str, intent: str = "", test_name: str = "") -> str | None:
        if not self.api_key:
            return None

        resp = self._post("/heal", {
            "selector":   selector,
            "html":       html,
            "intent":     intent,
            "test_name":  test_name,
            "session_id": self._session_id or "",
        })
        if not resp:
            return None

        if resp.get("success"):
            healed = resp["healed"]
            self._log(
                f"✅ Healed [{resp.get('strategy','?')}] "
                f"score={resp.get('dom_score', 0)} | "
                f"{selector[:35]} → {healed[:35]}"
            )
            with self._lock:
                self._heals.append({
                    "original": selector,
                    "healed":   healed,
                    "strategy": resp.get("strategy"),
                    "test":     test_name,
                })
            return healed
        else:
            self._log(f"❌ Could not heal: {selector[:60]}", level="warn")
            with self._lock:
                self._failures.append(
                    {"selector": selector, "test": test_name})
            return None

    # ── Framework activation ───────────────────────────────────────────────────

    def activate(self, framework: str = "auto"):
        if framework == "auto":
            framework = _detect_framework()
            self._log(f"Auto-detected framework: {framework}")

        if framework == "selenium":
            from healbot.adapters.selenium_adapter import SeleniumAdapter
            self._adapter = SeleniumAdapter(self)
        elif framework == "playwright":
            from healbot.adapters.playwright_adapter import PlaywrightAdapter
            self._adapter = PlaywrightAdapter(self)
        elif framework == "robot":
            from healbot.adapters.robot_adapter import RobotAdapter
            self._adapter = RobotAdapter(self)
        elif framework == "none":
            self._log("No framework patching — use hb.heal() manually")
            return
        else:
            self._warn(
                f"Unknown framework '{framework}' — use hb.heal() manually")
            return

        self._adapter.patch()
        self._log(f"Patched: {framework}")

    def deactivate(self):
        if self._adapter:
            self._adapter.unpatch()
            self._adapter = None
            self._log("Unpatched")

    # ── Internals ──────────────────────────────────────────────────────────────

    def _post(self, path: str, body: dict) -> dict:
        if not self.api_key:
            return {}
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            self._warn(f"API {e.code} on {path}: {e.read().decode()[:150]}")
        except urllib.error.URLError as e:
            self._warn(f"Cannot reach HealBot ({e.reason}) — healing skipped")
        except Exception as e:
            self._warn(f"Error: {e}")
        return {}

    def _log(self, msg: str, level: str = "info"):
        if self.verbose:
            prefix = "⚠ " if level == "warn" else "🔧 "
            print(f"[HealBot] {prefix}{msg}", flush=True)

    def _warn(self, msg: str):
        self._log(msg, level="warn")


def _detect_framework() -> str:
    import importlib
    for name in ["selenium", "playwright", "robot"]:
        try:
            importlib.import_module(name)
            return name
        except ImportError:
            continue
    return "none"
