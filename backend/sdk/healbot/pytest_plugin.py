"""
healbot/pytest_plugin.py — Zero-config pytest plugin.

Registered automatically via setup.py entry_points.
Activates when HEALBOT_API_KEY is set in environment.
"""

import os
import pytest

_hb = None


def pytest_configure(config):
    global _hb
    api_key = os.environ.get("HEALBOT_API_KEY", "").strip()
    if not api_key:
        return

    from healbot.client import HealBot
    _hb = HealBot(
        api_key=api_key,
        url=os.environ.get("HEALBOT_URL", "http://localhost:8000"),
        verbose=True,
    )

    if not _hb.ping():
        print(f"\n[HealBot] ⚠ Cannot reach {_hb.url} — healing disabled")
        _hb = None
        return

    # Auto-detect and patch framework
    _hb.activate()

    # Start session — creates batch + script_run + RunContext on HealBot
    suite_name = f"pytest — {os.path.basename(os.getcwd())}"
    _hb.start_session(name=suite_name, framework="selenium")

    print(f"\n[HealBot] ✅ Session active")
    print(
        f"[HealBot] 🖥  Watch live → {_hb.url.replace('8000','3000')} (Batches tab)")
    print(f"[HealBot] 🔗 Stream     → {_hb.url}/stream/{_hb._run_id}")


def pytest_runtest_setup(item):
    """Pass current test name to the HealBot instance before each test."""
    if _hb:
        # Store test name so selenium_adapter can read it during find_element
        _hb._current_test = item.nodeid


def pytest_sessionfinish(session, exitstatus):
    if not _hb:
        return

    report = _hb.session_report()
    _hb.end_session()
    _hb.deactivate()

    print("\n" + "─" * 58)
    print("  HealBot Session Summary")
    print("─" * 58)
    print(f"  Selectors healed  : {report['total_heals']}")
    print(f"  Healing failures  : {report['total_failures']}")
    print(f"  Heal rate         : {report['heal_rate']}%")
    if report["heals"]:
        print("\n  What was healed:")
        for h in report["heals"]:
            print(
                f"    [{h['strategy']:12}] {h['original'][:36]:36} → {h['healed'][:36]}")
    print("─" * 58)
    print(
        f"  Full report → {os.environ.get('HEALBOT_URL','http://localhost:8000').replace('8000','3000')} (Batches tab)")
    print("─" * 58)
