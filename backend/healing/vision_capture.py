"""
Screenshot capture. Each run saves to artifacts/<run_id>/ for a
per-run visual audit trail.
"""

import os
from datetime import datetime
from core.logger import log

ARTIFACTS_ROOT = os.path.join(os.path.dirname(__file__), "..", "artifacts")


def capture_screen(driver, run_id: str = "default", ctx=None) -> str | None:
    if driver is None:
        return None
    try:
        run_dir = os.path.join(ARTIFACTS_ROOT, run_id)
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(
            run_dir, f"screen_{datetime.now().strftime('%H%M%S_%f')}.png")
        driver.save_screenshot(path)
        log("VISION", f"Screenshot → {path}", ctx=ctx)
        if ctx:
            ctx.increment("visionCalls")
        return path
    except Exception as e:
        log("VISION", f"Screenshot failed: {e}", level="error", ctx=ctx)
        return None
