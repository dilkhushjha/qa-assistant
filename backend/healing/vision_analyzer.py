"""
Visual confirmation via Ollama llava.

After DOM/LLM picks a healed selector, this sends the screenshot to llava
asking: "is this element visible on screen?"

Returns: { "verdict": "confirmed"|"rejected"|"unknown", "note": "..." }

Setup: ollama pull llava
Falls back to verdict="unknown" if llava is unavailable — healing continues.
"""

import base64
import json
import os
import urllib.request
import urllib.error
from core.logger import log

OLLAMA_BASE = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434").replace("/api/generate", "")
LLAVA_MODEL = os.environ.get("LLAVA_MODEL", "llava")
TIMEOUT = 45


def analyze_screenshot(screenshot_path: str, intent: str, healed_selector: str, ctx=None) -> dict:
    _unknown = {"verdict": "unknown", "note": ""}

    if not screenshot_path or not os.path.exists(screenshot_path):
        return _unknown

    try:
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except IOError as e:
        log("VISION", f"Cannot read screenshot: {e}", level="error", ctx=ctx)
        return _unknown

    prompt = (
        f"Screenshot of a web page. I need to find: '{intent}'. "
        f"Healed XPath: {healed_selector}. "
        f"Is the element clearly visible and interactable? "
        f'Reply ONLY with JSON: {{"visible": true/false, "reason": "one sentence"}}'
    )

    payload = json.dumps({
        "model":  LLAVA_MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "format": "json",
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    log("VISION", f"Asking llava to confirm: {intent}", ctx=ctx)
    raw = ""
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = json.loads(resp.read()).get("response", "").strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        parsed = json.loads(raw)
        visible = parsed.get("visible")
        reason = parsed.get("reason", "")
        verdict = "confirmed" if visible is True else (
            "rejected" if visible is False else "unknown")

        log("VISION", f"Verdict: {verdict} — {reason}", ctx=ctx)
        return {"verdict": verdict, "note": reason}

    except urllib.error.URLError:
        log("VISION", "llava unavailable — skipping visual confirmation", ctx=ctx)
    except (json.JSONDecodeError, KeyError) as e:
        log("VISION", f"llava parse error: {e}", level="warning", ctx=ctx)

    return _unknown
