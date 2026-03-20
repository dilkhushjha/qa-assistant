"""
Ollama LLM backend for selector healing.
Requires: ollama pull llama3
Override: OLLAMA_URL, OLLAMA_MODEL env vars
"""

import json
import os
import urllib.request
import urllib.error
from core.logger import log

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
TIMEOUT = 60


def ask_llm_for_element(context: list, intent: str, ctx=None) -> dict | None:
    """
    Ask Ollama to identify the correct element for the given intent.
    Returns dict with id/name/data_testid/reason, or None on failure.
    """
    log("LLM", f"Querying Ollama ({OLLAMA_MODEL}) — intent: {intent}", ctx=ctx)
    if ctx:
        ctx.increment("llmCalls")

    slim = [
        {k: el[k] for k in
         ("id", "name", "placeholder", "tag", "text", "aria_label", "data_testid")
         if el.get(k)}
        for el in context
    ]

    prompt = f"""You are a web automation expert. A Selenium selector is broken. Find the correct element.

Intent: {intent}

Page elements (JSON):
{json.dumps(slim, indent=2)}

Reply ONLY with a JSON object — no markdown, no code fences, nothing else:
{{
  "id": "<element id or null>",
  "name": "<element name or null>",
  "data_testid": "<data-testid or null>",
  "reason": "<one sentence why>"
}}"""

    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    raw = ""
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = json.loads(resp.read()).get("response", "").strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        parsed = json.loads(raw)
        log("LLM",
            f"✅ id={parsed.get('id')} — {parsed.get('reason','')}", ctx=ctx)
        return parsed

    except urllib.error.URLError as e:
        log("LLM", f"Ollama unreachable: {e.reason}", level="error", ctx=ctx)
    except (json.JSONDecodeError, KeyError) as e:
        log("LLM",
            f"Parse error: {e} | raw: {raw[:200]}", level="error", ctx=ctx)
    return None
