"""
analytics.py router — Insights, trends, flakiness detection.

GET /analytics/overview     High-level stats (heal rate, trends, top failures)
GET /analytics/flakiness    Scripts that fail and pass intermittently
GET /analytics/selectors    Most-healed selectors (top breakages)
GET /analytics/usage        Daily usage vs tier limits
"""

from fastapi import APIRouter, Request
from sqlalchemy import select, func
from core.database import (
    engine, script_runs, heal_events, usage_log, batches,
    get_analytics
)
from core.config import TIER_LIMITS
from collections import defaultdict
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def overview(request: Request, days: int = 30):
    tenant = request.state.tenant
    return get_analytics(tenant["id"], days)


@router.get("/flakiness")
def flakiness(request: Request, limit: int = 20):
    """
    Detect flaky scripts: scripts that have both passed and failed
    across different runs. Sorted by flakiness score (fail_rate).
    """
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(script_runs).where(script_runs.c.tenant_id == tenant["id"])
            .order_by(script_runs.c.created_at.desc()).limit(500)
        ).mappings().all()

    # Group by script_name
    by_name: dict = defaultdict(
        lambda: {"passed": 0, "failed": 0, "healed": 0, "runs": 0})
    for r in rows:
        n = r["script_name"]
        by_name[n]["runs"] += 1
        if r["status"] in ("passed", "healed"):
            by_name[n]["passed"] += 1
        if r["status"] == "healed":
            by_name[n]["healed"] += 1
        if r["status"] == "failed":
            by_name[n]["failed"] += 1

    # Flaky = has both passes and failures
    flaky = []
    for name, counts in by_name.items():
        if counts["passed"] > 0 and counts["failed"] > 0:
            fail_rate = round(counts["failed"] / counts["runs"] * 100, 1)
            flaky.append({
                "script_name": name,
                "total_runs":  counts["runs"],
                "passed":      counts["passed"],
                "healed":      counts["healed"],
                "failed":      counts["failed"],
                "fail_rate":   fail_rate,
                "flakiness_score": fail_rate,
            })

    flaky.sort(key=lambda x: x["flakiness_score"], reverse=True)
    return flaky[:limit]


@router.get("/selectors")
def top_broken_selectors(request: Request, limit: int = 20):
    """Most frequently broken selectors — guides where to invest in fixes."""
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(heal_events).where(heal_events.c.tenant_id == tenant["id"])
            .order_by(heal_events.c.created_at.desc()).limit(2000)
        ).mappings().all()

    counts: dict = defaultdict(
        lambda: {"total": 0, "healed": 0, "strategy": {}})
    for h in rows:
        sel = h["selector"] or "unknown"
        counts[sel]["total"] += 1
        if h["success"]:
            counts[sel]["healed"] += 1
        s = h["strategy"] or "unknown"
        counts[sel]["strategy"][s] = counts[sel]["strategy"].get(s, 0) + 1

    result = [
        {
            "selector":       sel,
            "break_count":    d["total"],
            "healed_count":   d["healed"],
            "heal_rate":      round(d["healed"] / d["total"] * 100, 1),
            "top_strategy":   max(d["strategy"], key=d["strategy"].get) if d["strategy"] else None,
        }
        for sel, d in counts.items()
    ]
    result.sort(key=lambda x: x["break_count"], reverse=True)
    return result[:limit]


@router.get("/usage")
def usage(request: Request):
    """Daily usage vs tier limits for the past 30 days."""
    tenant = request.state.tenant
    tier = tenant.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    tenant_id = tenant["id"]

    with engine.connect() as conn:
        rows = conn.execute(
            select(usage_log).where(usage_log.c.tenant_id == tenant_id)
            .order_by(usage_log.c.date.desc()).limit(30)
        ).mappings().all()

    today = datetime.now().strftime("%Y-%m-%d")
    today_row = next((r for r in rows if r["date"] == today), None)

    return {
        "tier":              tier,
        "daily_limit":       limits["scripts_per_day"],
        "used_today":        today_row["scripts_run"] if today_row else 0,
        "heals_today":       today_row["heals"] if today_row else 0,
        "llm_calls_today":   today_row["llm_calls"] if today_row else 0,
        "history":           [dict(r) for r in rows],
    }
