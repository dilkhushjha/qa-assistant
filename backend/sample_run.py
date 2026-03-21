"""
sample_run.py — HealBot end-to-end demo.
Run from project root: python sample_run.py

What it does:
  1. Starts the API server on port 8765 in a background thread
  2. Registers a tenant and gets an API key
  3. Submits the saucedemo journey (9 broken selectors)
  4. Polls progress and prints live status
  5. Prints the final healing report

Requirements:
    pip install selenium fastapi uvicorn sqlalchemy beautifulsoup4 pydantic
    Chrome + ChromeDriver installed and on PATH
    Ollama optional: ollama pull llama3
"""
import sys
import os
import time
import json
import threading
import urllib.request
import urllib.error
import secrets

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if not os.path.isdir(BACKEND_DIR):
    print(f"ERROR: backend/ not found at {BACKEND_DIR}")
    sys.exit(1)

sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)   # so data/, memory/, artifacts/ resolve correctly

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
        return json.loads(e.read() or b"{}"), e.code


def wait_for_server(retries=30):
    for _ in range(retries):
        try:
            urllib.request.urlopen(f"{API_BASE}/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def poll_batch(batch_id, key):
    while True:
        data, _ = api("GET", f"/batches/{batch_id}", key=key)
        status = data.get("status", "?")
        total = data.get("total_scripts", 0)
        completed = data.get("completed", 0)
        passed = data.get("passed", 0)
        healed = data.get("healed", 0)
        failed = data.get("failed", 0)
        filled = int(completed / total * 30) if total else 0
        bar = "█" * filled + "░" * (30 - filled)
        print(f"\r  [{bar}] {completed}/{total}  ✓{passed} ⚡{healed} ✕{failed}  {status.upper()}   ",
              end="", flush=True)
        if status in ("completed", "failed", "cancelled"):
            print()
            return data
        time.sleep(1)


JOURNEY = {
    "name": "Sauce Demo — Login to Checkout",
    "steps": [
        {"id": "open_site",        "description": "Open Sauce Demo",       "url": "https://www.saucedemo.com/", "action": "wait",
            "selector": "//div[@class='login_logo']",        "value": None,          "intent": "page load confirmation",           "critical": True},
        {"id": "enter_username",   "description": "Enter username",        "url": None, "action": "type",
            "selector": "//input[@id='broken-username']",    "value": "standard_user", "intent": "username input field",             "critical": True},
        {"id": "enter_password",   "description": "Enter password",        "url": None, "action": "type",
            "selector": "//input[@id='broken-password']",    "value": "secret_sauce", "intent": "password input field",             "critical": True},
        {"id": "click_login",      "description": "Click Login",           "url": None, "action": "click",
            "selector": "//input[@id='broken-login-btn']",   "value": None,           "intent": "login submit button",              "critical": True},
        {"id": "assert_inventory", "description": "Inventory page loaded", "url": None, "action": "assert_url", "selector": None,
            "value": "/inventory",   "intent": "url verification",                 "critical": True},
        {"id": "add_to_cart",      "description": "Add Backpack to cart",  "url": None, "action": "click",
            "selector": "//button[@id='broken-add-backpack']", "value": None,          "intent": "add to cart button",               "critical": False},
        {"id": "open_cart",        "description": "Open cart",             "url": None, "action": "click",
            "selector": "//a[@class='shopping_cart_link']",  "value": None,           "intent": "shopping cart link",               "critical": False},
        {"id": "assert_cart",      "description": "Cart page loaded",      "url": None, "action": "assert_url", "selector": None,
            "value": "/cart",        "intent": "url verification",                 "critical": False},
        {"id": "checkout",         "description": "Click Checkout",        "url": None, "action": "click",
            "selector": "//button[@id='broken-checkout']",   "value": None,           "intent": "checkout button",                  "critical": False},
        {"id": "fill_first_name",  "description": "Fill first name",       "url": None, "action": "type",
            "selector": "//input[@id='broken-fname']",        "value": "John",         "intent": "first name input field",           "critical": False},
        {"id": "fill_last_name",   "description": "Fill last name",        "url": None, "action": "type",
            "selector": "//input[@id='broken-lname']",        "value": "Doe",          "intent": "last name input field",            "critical": False},
        {"id": "fill_zip",         "description": "Fill postal code",      "url": None, "action": "type",
            "selector": "//input[@id='broken-zip']",          "value": "10001",        "intent": "postal code zip input field",      "critical": False},
        {"id": "continue_checkout", "description": "Continue to summary",   "url": None, "action": "click",
            "selector": "//input[@id='broken-continue']",     "value": None,           "intent": "continue button on checkout form",  "critical": False},
        {"id": "assert_overview",  "description": "Order overview loaded", "url": None, "action": "assert_url", "selector": None,
            "value": "/checkout-step-two", "intent": "url verification",             "critical": False},
    ]
}


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     HealBot SaaS — End-to-End Sample Run                 ║
║     Target: https://www.saucedemo.com                    ║
╚══════════════════════════════════════════════════════════╝
""")

    # 1. Start server
    print("① Starting API server on port 8765…")
    import uvicorn

    def start():
        uvicorn.run("main:app", host="127.0.0.1",
                    port=8765, log_level="warning")

    threading.Thread(target=start, daemon=True).start()

    if not wait_for_server():
        print("  ❌ Server failed to start — is port 8765 free?")
        sys.exit(1)
    print("  ✅ Server ready\n")

    # 2. Register
    print("② Registering tenant…")
    email = f"demo_{secrets.token_hex(4)}@acme.com"
    resp, status = api("POST", "/auth/register",
                       {"name": "Acme Corp", "email": email, "tier": "pro"})
    if status != 200:
        print(f"  ❌ Failed: {resp}")
        sys.exit(1)

    KEY = resp["api_key"]
    TENANT_ID = resp["tenant_id"]
    print(f"  ✅ Tenant: Acme Corp  (id={TENANT_ID}  tier=pro)")
    print(f"  🔑 API Key: {KEY}\n")

    # 3. Submit batch
    broken = [s for s in JOURNEY["steps"] if s.get(
        "selector") and "broken" in s["selector"]]
    print(f"③ Submitting journey: {JOURNEY['name']}")
    print(
        f"   {len(JOURNEY['steps'])} steps · {len(broken)} broken selectors (will auto-heal)\n")

    resp, status = api("POST", "/batches",
                       {"name": "Sample Run", "scripts": [JOURNEY]}, key=KEY)
    if status != 200:
        print(f"  ❌ Failed: {resp}")
        sys.exit(1)

    BATCH_ID = resp["batch_id"]
    print(f"  ✅ Batch queued → id={BATCH_ID}\n")

    # 4. Watch progress
    print("④ Running… Chrome will open and heal selectors in real time")
    final = poll_batch(BATCH_ID, KEY)
    print()

    # 5. Report
    report, _ = api("GET", f"/batches/{BATCH_ID}/report", key=KEY)
    strats = report.get("strategy_breakdown", {})
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Run Report                                              ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Status     : {report.get('status','?').upper():<44}║")
    print(f"║  Passed     : {report.get('passed',0):<44}║")
    print(f"║  Healed     : {report.get('healed',0):<44}║")
    print(f"║  Failed     : {report.get('failed',0):<44}║")
    print(f"║  Heal Rate  : {str(report.get('heal_rate_pct',0))+'%':<44}║")
    if strats:
        print("╠══════════════════════════════════════════════════════════╣")
        print("║  Strategies used:                                        ║")
        for s, n in strats.items():
            print(f"║    {s:<12}: {n:<38}║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print(f"  💾 Healed selectors saved — next run will be instant (memory hits)")
    print(f"  📊 Dashboard: http://localhost:5173")
    print(f"  🔑 API Key: {KEY}")


if __name__ == "__main__":
    main()
