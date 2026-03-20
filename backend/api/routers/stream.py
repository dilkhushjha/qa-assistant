"""
stream.py router — Server-Sent Events for live run streaming.

GET /stream/{run_id}   — streams logs + metrics for a single script run
GET /stream/batch/{id} — streams batch-level progress (completed/total counter)
"""

import json
import time
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from core import run_context
from core.database import engine, batches, script_runs
from sqlalchemy import select

router = APIRouter(prefix="/stream", tags=["Stream"])


@router.get("/{run_id}")
def stream_run(run_id: str, request: Request):
    ctx = run_context.get(run_id)

    if not ctx:
        # Run may have already finished — send snapshot from DB and close
        with engine.connect() as conn:
            row = conn.execute(
                select(script_runs).where(script_runs.c.id == run_id)
            ).mappings().first()
        if not row:
            raise HTTPException(404, f"Run {run_id} not found")

        def _done():
            yield f"data: {json.dumps({'type':'done','payload':{'status':row['status'],'run_id':run_id}})}\n\n"
        return StreamingResponse(_done(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def _live():
        sent = 0
        while True:
            for entry in ctx.get_logs(since=sent):
                yield f"data: {json.dumps({'type':'log','payload':entry})}\n\n"
                sent += 1
            yield f"data: {json.dumps({'type':'snapshot','payload':{'metrics':ctx.get_metrics(),'status':ctx.get_status(),'run_id':run_id}})}\n\n"
            if ctx.get_status() in ("passed", "failed", "healed", "error"):
                yield f"data: {json.dumps({'type':'done','payload':{'status':ctx.get_status(),'run_id':run_id}})}\n\n"
                break
            time.sleep(0.4)

    return StreamingResponse(_live(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/batch/{batch_id}")
def stream_batch(batch_id: str, request: Request):
    """Streams batch progress: completed/total counter every second."""
    def _batch():
        while True:
            with engine.connect() as conn:
                row = conn.execute(
                    select(batches).where(batches.c.id == batch_id)
                ).mappings().first()
            if not row:
                yield f"data: {json.dumps({'type':'error','message':'batch not found'})}\n\n"
                break
            yield f"data: {json.dumps({'type':'progress','payload':{'batch_id':batch_id,'status':row['status'],'total':row['total_scripts'],'completed':row['completed'],'passed':row['passed'],'healed':row['healed'],'failed':row['failed']}})}\n\n"
            if row["status"] in ("completed", "failed", "cancelled"):
                yield f"data: {json.dumps({'type':'done','payload':{'status':row['status']}})}\n\n"
                break
            time.sleep(1)

    return StreamingResponse(_batch(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
