from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from core.database import engine, intent_maps, now
from healing.intent_engine import register_intent_map

router = APIRouter(prefix="/intent-maps", tags=["Intent Maps"])


class IntentMapRequest(BaseModel):
    mappings: list   # [{"keywords":[...], "intent":"..."}]


@router.post("")
def set_map(req: IntentMapRequest, request: Request):
    tenant = request.state.tenant
    tenant_id = tenant["id"]

    register_intent_map(tenant_id, req.mappings)

    with engine.begin() as conn:
        exists = conn.execute(
            select(intent_maps).where(intent_maps.c.tenant_id == tenant_id)
        ).first()
        if exists:
            conn.execute(update(intent_maps)
                         .where(intent_maps.c.tenant_id == tenant_id)
                         .values(mappings=req.mappings, updated_at=now()))
        else:
            conn.execute(intent_maps.insert().values(
                tenant_id=tenant_id, mappings=req.mappings, updated_at=now()
            ))

    return {"status": "ok", "rules": len(req.mappings)}


@router.get("")
def get_map(request: Request):
    tenant = request.state.tenant
    with engine.connect() as conn:
        row = conn.execute(
            select(intent_maps).where(intent_maps.c.tenant_id == tenant["id"])
        ).mappings().first()
    return dict(row) if row else {"mappings": []}
