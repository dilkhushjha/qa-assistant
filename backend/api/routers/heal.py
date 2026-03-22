"""
heal.py — Inline single-selector healing endpoint.

Called by healbot-sdk on every NoSuchElementException.
When a session_id is provided:
  - Looks up the RunContext → pushes log entries (SSE streams them live)
  - Writes heal_event row  (audit trail, analytics)
  - Writes step_result row (shows step state in dashboard Run tab)
  - Updates batch counters (live progress bar)
"""
from healing.healing_engine import heal_selector
from core.logger import log as _log
from core.database import engine, batches, script_runs, heal_events, upsert_step, now
from sqlalchemy import update
from pydantic import BaseModel
from fastapi import APIRouter, Request
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


router = APIRouter(prefix="/heal", tags=["Heal"])


class HealRequest(BaseModel):
    selector:   str
    html:       str
    intent:     str = ""
    test_name:  str = ""
    session_id: str = ""   # links to a session started via /sessions/start


class HealResponse(BaseModel):
    healed:    str | None
    strategy:  str | None
    dom_score: int
    llm_used:  bool
    success:   bool


@router.post("", response_model=HealResponse)
def heal(req: HealRequest, request: Request):
    tenant = request.state.tenant
    tenant_id = tenant["id"]

    # Look up session context if provided
    sess = None
    ctx = None
    if req.session_id:
        from api.routers.sessions import get_session
        sess = get_session(req.session_id)
        if sess:
            ctx = sess["ctx"]

    # Generate a stable step_id from the selector + test name
    import hashlib
    step_id = hashlib.md5(
        f"{req.test_name}:{req.selector}".encode()).hexdigest()[:8]

    # Log the attempt (shows in live log stream on dashboard)
    _log("ENGINE",
         f"Healing [{req.test_name or 'unknown'}]: {req.selector[:60]}", ctx=ctx)

    # Mark step as running in dashboard
    if sess:
        upsert_step(sess["run_id"], step_id, tenant_id,
                    description=req.test_name or req.selector[:40],
                    action="find_element",
                    original_selector=req.selector,
                    status="running",
                    started_at=now(),
                    )

    # Run the healing pipeline
    result = heal_selector(
        old_selector=req.selector,
        new_html=req.html,
        intent=req.intent or None,
        tenant_id=tenant_id,
        run_id=sess["run_id"] if sess else (req.session_id or "inline"),
        step_id=step_id,
        ctx=ctx,
    )
    success = result["healed"] is not None

    # Write to DB and update dashboard state
    if sess:
        run_id = sess["run_id"]
        batch_id = sess["batch_id"]

        # Write heal_event — shows in analytics
        with engine.begin() as conn:
            conn.execute(heal_events.insert().values(
                run_id=run_id,
                tenant_id=tenant_id,
                step_id=step_id,
                selector=req.selector,
                intent=req.intent or "",
                dom_score=result["dom_score"],
                dom_candidate=result["dom_candidate"],
                llm_invoked=result["llm_invoked"],
                llm_candidate=result["llm_candidate"],
                final_selector=result["healed"],
                strategy=result["strategy"],
                success=success,
                created_at=now(),
            ))

        # Update step_result — shows step state (healed/fail) in dashboard Run tab
        step_status = "healed" if success else "fail"
        upsert_step(run_id, step_id, tenant_id,
                    status=step_status,
                    healed_selector=result["healed"],
                    strategy=result["strategy"],
                    finished_at=now(),
                    )

        # Push step event to RunContext — dashboard Run tab updates live via SSE
        ctx.push({
            "type":              "step",
            "step_id":           step_id,
            "status":            step_status,
            "original_selector": req.selector,
            "healed_selector":   result["healed"],
            "reason":            "" if success else "All healing strategies exhausted",
            "vision_verdict":    result.get("vision_verdict", "unknown"),
            "vision_note":       result.get("vision_note", ""),
        })

        # Update session counters
        if success:
            sess["healed"] += 1
            ctx.increment("healedSelectors")
        else:
            sess["failed"] += 1
            ctx.increment("failures")

        if result["llm_invoked"]:
            ctx.increment("llmCalls")

        # Update batch progress counters (live progress bar on dashboard)
        with engine.begin() as conn:
            conn.execute(
                update(batches).where(batches.c.id == batch_id).values(
                    healed=sess["healed"],
                    failed=sess["failed"],
                )
            )

    return HealResponse(
        healed=result["healed"],
        strategy=result["strategy"],
        dom_score=result["dom_score"],
        llm_used=result["llm_invoked"],
        success=success,
    )
