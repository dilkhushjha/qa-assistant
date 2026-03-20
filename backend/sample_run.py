"""
sample_run.py — HealBot SaaS end-to-end sample run.

This script does everything in sequence:
  1. Starts the API server in a background thread
  2. Registers a tenant and gets an API key
  3. Defines a journey with intentionally broken selectors
  4. Submits it as a batch
  5. Streams live progress to the console
  6. Prints the final report

Run from your project root (v7/):
    python sample_run.py

Requirements:
    pip install selenium fastapi uvicorn sqlalchemy beautifulsoup4 pydantic
    Chrome + ChromeDriver must be installed and on PATH
    Ollama (optional): ollama pull llama3
"""

import sys
import os
import time
import json
import threading
import urllib.request
import urllib.error

# ── Add backend/ to path ──────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)   # so data/, memory/, artifacts/ resolve correctly

# dedicated port so we don't clash with anything
API_BASE = "http://localhost:8765"


# ── Helpers ───────────────────────────────────────────────────────────────────

def api(method, path, body=None, key=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def wait_for_server(retries=30):
    for _ in range(retries):
        try:
            urllib.request.urlopen(f"{API_BASE}/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def stream_batch(batch_id, key):
    """Poll batch progress until complete."""
    while True:
        data, _ = api("GET", f"/batches/{batch_id}", key=key)
        status = data.get("status", "?")
        total = data.get("total_scripts", 0)
        completed = data.get("completed", 0)
        passed = data.get("passed", 0)
        healed = data.get("healed", 0)
        failed = data.get("failed", 0)

        bar_filled = int((completed / total * 30)) if total else 0
        bar = "█" * bar_filled + "░" * (30 - bar_filled)
        print(f"\r  [{bar}] {completed}/{total}  "
              f"✓{passed} ⚡{healed} ✕{failed}  {status.upper()}   ", end="", flush=True)

        if status in ("completed", "failed", "cancelled"):
            print()  # newline after progress bar
            return data
        time.sleep(1)


# ── The sample journey ────────────────────────────────────────────────────────
# Full saucedemo.com Login → Add to Cart → Checkout
# 9 selectors are intentionally broken to demo healing

SAMPLE_JOURNEY = {
    "name": "Sauce Demo — Full E2E",
    "steps": [
        {
            "id": "open_site",
            "description": "Open Sauce Demo",
            "url": "https://www.saucedemo.com/",
            "action": "wait",
            "selector": "//div[@class='login_logo']",   # correct
            "value": None,
            "intent": "page load confirmation",
            "critical": True,
        },
        {
            "id": "enter_username",
            "description": "Enter username",
            "url": None,
            "action": "type",
            "selector": "//input[@id='broken-username']",   # BROKEN
            "value": "standard_user",
            "intent": "username input field",
            "critical": True,
        },
        {
            "id": "enter_password",
            "description": "Enter password",
            "url": None,
            "action": "type",
            "selector": "//input[@id='broken-password']",   # BROKEN
            "value": "secret_sauce",
            "intent": "password input field",
            "critical": True,
        },
        {
            "id": "click_login",
            "description": "Click Login",
            "url": None,
            "action": "click",
            "selector": "//input[@id='broken-login-btn']",  # BROKEN
            "value": None,
            "intent": "login submit button",
            "critical": True,
        },
        {
            "id": "assert_inventory",
            "description": "Assert inventory page loaded",
            "url": None,
            "action": "assert_url",
            "selector": None,
            "value": "/inventory",
            "intent": "url verification",
            "critical": True,
        },
        {
            "id": "add_to_cart",
            "description": "Add Backpack to cart",
            "url": None,
            "action": "click",
            "selector": "//button[@id='broken-add-backpack']",  # BROKEN
            "value": None,
            "intent": "add to cart button",
            "critical": False,
        },
        {
            "id": "open_cart",
            "description": "Open cart",
            "url": None,
            "action": "click",
            "selector": "//a[@class='shopping_cart_link']",  # correct
            "value": None,
            "intent": "shopping cart link",
            "critical": False,
        },
        {
            "id": "assert_cart",
            "description": "Assert cart page",
            "url": None,
            "action": "assert_url",
            "selector": None,
            "value": "/cart",
            "intent": "url verification",
            "critical": False,
        },
        {
            "id": "checkout",
            "description": "Click Checkout",
            "url": None,
            "action": "click",
            "selector": "//button[@id='broken-checkout']",  # BROKEN
            "value": None,
            "intent": "checkout button",
            "critical": False,
        },
        {
            "id": "fill_first_name",
            "description": "Fill first name",
            "url": None,
            "action": "type",
            "selector": "//input[@id='broken-fname']",  # BROKEN
            "value": "John",
            "intent": "first name input field",
            "critical": False,
        },
        {
            "id": "fill_last_name",
            "description": "Fill last name",
            "url": None,
            "action": "type",
            "selector": "//input[@id='broken-lname']",  # BROKEN
            "value": "Doe",
            "intent": "last name input field",
            "critical": False,
        },
        {
            "id": "fill_zip",
            "description": "Fill postal code",
            "url": None,
            "action": "type",
            "selector": "//input[@id='broken-zip']",  # BROKEN
            "value": "10001",
            "intent": "postal code zip input field",
            "critical": False,
        },
        {
            "id": "continue_checkout",
            "description": "Continue to order summary",
            "url": None,
            "action": "click",
            "selector": "//input[@id='broken-continue']",  # BROKEN
            "value": None,
            "intent": "continue button on checkout form",
            "critical": False,
        },
        {
            "id": "assert_overview",
            "description": "Assert order overview",
            "url": None,
            "action": "assert_url",
            "selector": None,
            "value": "/checkout-step-two",
            "intent": "url verification",
            "critical": False,
        },
    ]
}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     HealBot SaaS — End-to-End Sample Run                 ║
║     Target: https://www.saucedemo.com                    ║
╚══════════════════════════════════════════════════════════╝
""")

    # ── 1. Start API server ───────────────────────────────────────────────────
    print("① Starting API server on port 8765…")

    import uvicorn
    import main as app_module

    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8765,
            log_level="warning",   # suppress uvicorn noise
        ),
        daemon=True,
    )
    server_thread.start()

    if not wait_for_server():
        print("  ❌ Server failed to start. Check port 8765 is free.")
        sys.exit(1)

    print("  ✅ Server ready at http://localhost:8765\n")

    # ── 2. Register tenant ────────────────────────────────────────────────────
    print("② Registering tenant…")
    import secrets
    email = f"demo_{secrets.token_hex(4)}@acme.com"

    resp, status = api("POST", "/auth/register", {
        "name":  "Acme Corp",
        "email": email,
        "tier":  "pro",
    })
    if status != 200:
        print(f"  ❌ Registration failed: {resp}")
        sys.exit(1)

    API_KEY = resp["api_key"]
    TENANT_ID = resp["tenant_id"]
    print(f"  ✅ Tenant: Acme Corp  (id={TENANT_ID}  tier=pro)")
    print(f"  🔑 API Key: {API_KEY}\n")

    # ── 3. Submit batch ───────────────────────────────────────────────────────
    print("③ Submitting batch (1 script, 14 steps)…")
    print(f"  Journey: {SAMPLE_JOURNEY['name']}")

    broken = [s for s in SAMPLE_JOURNEY["steps"]
              if s.get("selector") and "broken" in s["selector"]]
    print(
        f"  Broken selectors: {len(broken)}/14 (intentional — will be healed)")
    print()

    resp, status = api("POST", "/batches", {
        "name":    "Sample E2E Batch",
        "scripts": [SAMPLE_JOURNEY],
    }, key=API_KEY)

    if status != 200:
        print(f"  ❌ Batch submit failed: {resp}")
        sys.exit(1)

    BATCH_ID = resp["batch_id"]
    print(f"  ✅ Batch queued  →  id={BATCH_ID}\n")

    # ── 4. Stream progress ────────────────────────────────────────────────────
    print("④ Running… (watch Chrome open and heal in real time)")
    print()
    final = stream_batch(BATCH_ID, API_KEY)
    print()

    # ── 5. Fetch full report ──────────────────────────────────────────────────
    print("⑤ Fetching report…")
    report, _ = api("GET", f"/batches/{BATCH_ID}/report", key=API_KEY)
    print()

    # ── 6. Print results ──────────────────────────────────────────────────────
    total = report.get("total_scripts", 1)
    passed = report.get("passed", 0)
    healed = report.get("healed", 0)
    failed = report.get("failed", 0)
    heal_rt = report.get("heal_rate_pct", 0)
    strats = report.get("strategy_breakdown", {})

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Run Report                                              ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Status     : {report.get('status','?').upper():<44}║")
    print(f"║  Scripts    : {total:<44}║")
    print(f"║  Passed     : {passed:<44}║")
    print(f"║  Healed     : {healed:<44}║")
    print(f"║  Failed     : {failed:<44}║")
    print(f"║  Heal rate  : {str(heal_rt)+'%':<44}║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  Healing strategies used:                                ║")
    for s, n in strats.items():
        print(f"║    {s:<12} : {n:<38}║")
    print("╠══════════════════════════════════════════════════════════╣")

    # Per-script breakdown
    for script in report.get("script_summaries", []):
        print(f"║  {script['script_name'][:54]:<54}║")
        print(f"║    status={script['status']}  healed={script.get('healed_steps',0)}"
              f"  failed={script.get('failed_steps',0)}"
              f"  llm={script.get('llm_calls',0)}"
              f"  time={round((script.get('duration_ms') or 0)/1000,1)}s{'':<10}║")

    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  💾 Healed selectors saved to memory/ — next run will be instant")
    print("  📊 Full analytics: GET /analytics/overview")
    print(f"  🔑 Keep your API key: {API_KEY}")
    print()

    # ── 7. Show analytics ─────────────────────────────────────────────────────
    analytics, _ = api("GET", "/analytics/overview", key=API_KEY)
    if analytics:
        print("⑥ Analytics snapshot:")
        print(f"   Total scripts run : {analytics.get('total_scripts', 0)}")
        print(f"   Total heals       : {analytics.get('total_heals', 0)}")
        print(f"   Heal rate         : {analytics.get('heal_rate_pct', 0)}%")
        strategies = analytics.get("strategy_breakdown", {})
        if strategies:
            print(f"   Strategies        : {strategies}")
    print()
    print("✅ Done. Server still running — visit http://localhost:8765/docs")


if __name__ == "__main__":
    main()
