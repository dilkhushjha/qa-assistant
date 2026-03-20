"""
batches.py router — Submit and query script batches.

POST /batches            Submit a batch of journeys
GET  /batches            List all batches for tenant
GET  /batches/{id}       Batch detail + script run summaries
GET  /batches/{id}/runs  Script runs within a batch
GET  /batches/{id}/report  Full analytics report for a batch
"""
# ── sys.path fix ──
from journey_runner import run_journey
from journey_schema import validate, normalise
from core.config import TIER_LIMITS
from core.batch_scheduler import submit_batch, queue_depth
from core.database import engine, batches, script_runs, step_results, heal_events, now
from sqlalchemy import select
from fastapi import APIRouter, HTTPException, Request
import sys as _sys
import os as _os
_BACKEND_DIR = _os.path.abspath(__file__)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)
# ── sys.path fix ──


router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post("")
def submit(payload: dict, request: Request):
    """
    Submit a batch. Payload:
    {
      "name": "Sprint 42 regression",
      "project_id": "proj_abc",          // optional
      "scripts": [ <journey_json>, ... ]  // array of journey objects
    }
    """
    tenant = request.state.tenant
    name = payload.get("name", "Unnamed batch")
    project_id = payload.get("project_id")
    scripts = payload.get("scripts", [])

    if not scripts:
        raise HTTPException(422, "Batch must contain at least one script")

    # Validate + normalise each script
    normalised = []
    for i, s in enumerate(scripts):
        ok, err = validate(s)
        if not ok:
            raise HTTPException(
                422, f"Script {i+1} ({s.get('name','?')}): {err}")
        normalised.append(normalise(s))

    try:
        batch_id = submit_batch(
            tenant=tenant,
            project_id=project_id,
            batch_name=name,
            script_list=normalised,
            runner_fn=run_journey,
            submitted_by="api",
        )
    except PermissionError as e:
        raise HTTPException(429, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to queue batch: {e}")

    tier = tenant.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    return {
        "batch_id":    batch_id,
        "status":      "queued",
        "scripts":     len(normalised),
        "queue_depth": queue_depth(),
        "tier":        tier,
        "daily_limit": limits["scripts_per_day"],
    }


@router.get("")
def list_batches(request: Request, limit: int = 50):
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(batches)
            .where(batches.c.tenant_id == tenant["id"])
            .order_by(batches.c.created_at.desc())
            .limit(limit)
        ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{batch_id}")
def get_batch(batch_id: str, request: Request):
    tenant = request.state.tenant
    with engine.connect() as conn:
        batch = conn.execute(
            select(batches).where(
                batches.c.id == batch_id,
                batches.c.tenant_id == tenant["id"]
            )
        ).mappings().first()
        if not batch:
            raise HTTPException(404, "Batch not found")

        runs = conn.execute(
            select(script_runs).where(script_runs.c.batch_id == batch_id)
            .order_by(script_runs.c.script_index)
        ).mappings().all()

    return {**dict(batch), "runs": [dict(r) for r in runs]}


@router.get("/{batch_id}/runs")
def get_runs(batch_id: str, request: Request):
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(script_runs).where(
                script_runs.c.batch_id == batch_id,
                script_runs.c.tenant_id == tenant["id"]
            ).order_by(script_runs.c.script_index)
        ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{batch_id}/report")
def batch_report(batch_id: str, request: Request):
    """Full analytics report: per-script breakdown, heal events, strategy distribution."""
    tenant = request.state.tenant
    with engine.connect() as conn:
        batch = conn.execute(
            select(batches).where(
                batches.c.id == batch_id,
                batches.c.tenant_id == tenant["id"]
            )
        ).mappings().first()
        if not batch:
            raise HTTPException(404, "Batch not found")

        runs = conn.execute(
            select(script_runs).where(script_runs.c.batch_id == batch_id)
            .order_by(script_runs.c.script_index)
        ).mappings().all()

        heals = conn.execute(
            select(heal_events).where(
                heal_events.c.run_id.in_([r["id"] for r in runs])
            )
        ).mappings().all()

    # Strategy breakdown
    strategies: dict = {}
    for h in heals:
        s = h["strategy"] or "unknown"
        strategies[s] = strategies.get(s, 0) + 1

    # Per-script summary
    script_summaries = []
    for r in runs:
        script_summaries.append({
            "script_name":   r["script_name"],
            "status":        r["status"],
            "duration_ms":   r["duration_ms"],
            "healed_steps":  r["healed_steps"],
            "failed_steps":  r["failed_steps"],
            "llm_calls":     r["llm_calls"],
        })

    total = len(runs)
    passed = sum(1 for r in runs if r["status"] in ("passed", "healed"))
    failed = sum(1 for r in runs if r["status"] == "failed")
    heal_rt = round((batch["healed"] / total * 100) if total else 0, 1)

    return {
        "batch_id":          batch_id,
        "batch_name":        batch["name"],
        "status":            batch["status"],
        "total_scripts":     total,
        "passed":            passed,
        "healed":            batch["healed"],
        "failed":            failed,
        "heal_rate_pct":     heal_rt,
        "strategy_breakdown": strategies,
        "script_summaries":  script_summaries,
        "duration_s": round(
            (batch["finished_at"] - batch["started_at"]).total_seconds(), 1
        ) if batch["finished_at"] and batch["started_at"] else None,
    }
