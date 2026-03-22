"""
sessions.py — SDK session lifecycle.

When a QA team's test suite starts (via healbot-sdk), a session is created.
This session maps 1:1 with a batch + script_run so it appears on the dashboard
exactly like a journey run — live logs, step states, analytics, everything.

Flow:
  POST /sessions/start
    → creates batch record        (shows in Batches tab immediately)
    → creates script_run record   (groups all heals)
    → creates RunContext          (enables SSE live log stream)
    → returns { session_id, run_id }

  POST /heal  (called per broken selector)
    → heals the selector
    → pushes log entries to RunContext  (SSE streams them to dashboard)
    → writes heal_event row             (audit trail)
    → writes step_result row            (shows step state on dashboard)
    → updates batch counters            (live progress)

  POST /sessions/end
    → finalises script_run status
    → finalises batch status
    → RunContext stays alive for 60s then GC'd
"""
from core.logger import log as _log
from core.run_context import RunContext, register
from core.database import (
    engine, batches, script_runs, now,
    increment_usage, get_daily_usage
)
from sqlalchemy import update, select
from pydantic import BaseModel
from fastapi import APIRouter, Request
from datetime import datetime, timezone
import uuid
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


router = APIRouter(prefix="/sessions", tags=["Sessions"])

# In-memory map: session_id → { run_id, batch_id, ctx }
_sessions: dict = {}


class StartRequest(BaseModel):
    name:      str = ""
    framework: str = "unknown"


class EndRequest(BaseModel):
    session_id: str


@router.post("/start")
def start_session(req: StartRequest, request: Request):
    """
    Start a healing session.
    Creates a batch + script_run + RunContext so the dashboard can
    show this session live in the Batches tab and stream logs.
    """
    tenant = request.state.tenant
    tenant_id = tenant["id"]

    session_id = str(uuid.uuid4())[:8]
    batch_id = str(uuid.uuid4())[:8]
    run_id = str(uuid.uuid4())[:8]
    name = req.name or f"SDK Session — {datetime.now().strftime('%H:%M:%S')}"

    # Create batch record — shows up in Batches tab immediately
    with engine.begin() as conn:
        conn.execute(batches.insert().values(
            id=batch_id,
            tenant_id=tenant_id,
            project_id=None,
            name=name,
            status="running",
            total_scripts=1,
            completed=0,
            passed=0,
            healed=0,
            failed=0,
            created_at=now(),
            started_at=now(),
            submitted_by=f"sdk:{req.framework}",
        ))

        # Create script_run record — the single "script" for this session
        conn.execute(script_runs.insert().values(
            id=run_id,
            batch_id=batch_id,
            tenant_id=tenant_id,
            script_name=name,
            script_index=0,
            status="running",
            total_steps=0,
            created_at=now(),
            started_at=now(),
        ))

    # Create RunContext — enables SSE live streaming to /stream/{run_id}
    ctx = RunContext(run_id, name)
    ctx.set_status("running")
    register(ctx)

    _log("SESSION",
         f"Started [{session_id}] batch={batch_id} run={run_id} framework={req.framework}", ctx=ctx)

    # Store session state
    _sessions[session_id] = {
        "run_id":    run_id,
        "batch_id":  batch_id,
        "tenant_id": tenant_id,
        "ctx":       ctx,
        "name":      name,
        "healed":    0,
        "failed":    0,
    }

    return {
        "session_id": session_id,
        "run_id":     run_id,
        "batch_id":   batch_id,
        "stream_url": f"/stream/{run_id}",
        "status":     "running",
    }


@router.post("/end")
def end_session(req: EndRequest, request: Request):
    """
    End a session — finalise batch + script_run, close RunContext.
    """
    tenant = request.state.tenant
    tenant_id = tenant["id"]

    sess = _sessions.get(req.session_id)
    if not sess:
        return {"error": "session not found or already ended"}

    run_id = sess["run_id"]
    batch_id = sess["batch_id"]
    ctx = sess["ctx"]
    healed = sess["healed"]
    failed_c = sess["failed"]

    total = healed + failed_c
    heal_rt = round(healed / total * 100, 1) if total else 0

    # Determine final status
    final_status = "healed" if healed > 0 else (
        "passed" if failed_c == 0 else "failed")

    with engine.begin() as conn:
        conn.execute(
            update(script_runs).where(script_runs.c.id == run_id).values(
                status=final_status,
                healed_steps=healed,
                failed_steps=failed_c,
                finished_at=now(),
            )
        )
        conn.execute(
            update(batches).where(batches.c.id == batch_id).values(
                status="completed",
                completed=1,
                passed=1 if final_status in ("passed", "healed") else 0,
                healed=1 if final_status == "healed" else 0,
                failed=1 if final_status == "failed" else 0,
                finished_at=now(),
            )
        )

    # Increment usage stats
    date_str = datetime.now().strftime("%Y-%m-%d")
    increment_usage(tenant_id, date_str, scripts=1, heals=healed)

    # Signal SSE clients that the run is done
    ctx.set_status(final_status)
    _log("SESSION",
         f"Ended [{req.session_id}] healed={healed} failed={failed_c} heal_rate={heal_rt}%", ctx=ctx)

    del _sessions[req.session_id]

    return {
        "session_id": req.session_id,
        "run_id":     run_id,
        "batch_id":   batch_id,
        "healed":     healed,
        "failed":     failed_c,
        "total":      total,
        "heal_rate":  heal_rt,
        "status":     final_status,
    }


def get_session(session_id: str) -> dict | None:
    """Used by heal.py to look up the session context."""
    return _sessions.get(session_id)


@router.get("")
def list_sessions(request: Request, limit: int = 20):
    """List recent SDK sessions as batches."""
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(batches)
            .where(
                batches.c.tenant_id == tenant["id"],
                batches.c.submitted_by.like("sdk:%"),
            )
            .order_by(batches.c.created_at.desc())
            .limit(limit)
        ).mappings().all()
    return [dict(r) for r in rows]
