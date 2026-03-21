"""
auth.py router — Tenant registration and API key management.
POST /auth/register   → create tenant + first API key
POST /auth/keys       → generate additional API key
GET  /auth/keys       → list keys for current tenant
DELETE /auth/keys/{k} → revoke a key
"""
from core.database import engine, tenants, api_keys, now
from sqlalchemy import select, update
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
import secrets
import uuid
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    name:  str
    email: str
    tier:  str = "free"


class KeyRequest(BaseModel):
    name: str = "default"


@router.post("/register")
def register(req: RegisterRequest):
    tenant_id = str(uuid.uuid4())[:8]
    key = f"hb_live_{secrets.token_urlsafe(24)}"

    with engine.begin() as conn:
        existing = conn.execute(
            select(tenants).where(tenants.c.email == req.email)
        ).first()
        if existing:
            raise HTTPException(400, f"Email {req.email} already registered")

        conn.execute(tenants.insert().values(
            id=tenant_id, name=req.name, email=req.email,
            tier=req.tier, created_at=now(), is_active=True,
        ))
        conn.execute(api_keys.insert().values(
            key=key, tenant_id=tenant_id, name="default",
            created_at=now(), is_active=True,
        ))

    return {
        "tenant_id": tenant_id,
        "api_key":   key,
        "tier":      req.tier,
        "message":   "Keep your API key safe. Send it as: Authorization: Bearer <key>",
    }


@router.post("/keys")
def create_key(req: KeyRequest, request: Request):
    tenant = request.state.tenant
    key = f"hb_live_{secrets.token_urlsafe(24)}"
    with engine.begin() as conn:
        conn.execute(api_keys.insert().values(
            key=key, tenant_id=tenant["id"], name=req.name,
            created_at=now(), is_active=True,
        ))
    return {"api_key": key, "name": req.name}


@router.get("/keys")
def list_keys(request: Request):
    tenant = request.state.tenant
    with engine.connect() as conn:
        rows = conn.execute(
            select(api_keys).where(api_keys.c.tenant_id == tenant["id"])
        ).mappings().all()
    return [
        {"key": r["key"][:12] + "...", "name": r["name"],
         "created_at": r["created_at"], "last_used_at": r["last_used_at"],
         "is_active": r["is_active"]}
        for r in rows
    ]


@router.delete("/keys/{key_prefix}")
def revoke_key(key_prefix: str, request: Request):
    tenant = request.state.tenant
    with engine.begin() as conn:
        rows = conn.execute(
            select(api_keys).where(api_keys.c.tenant_id == tenant["id"])
        ).mappings().all()
        matched = [r for r in rows if r["key"].startswith(key_prefix)]
        if not matched:
            raise HTTPException(404, "Key not found")
        conn.execute(
            update(api_keys).where(api_keys.c.key == matched[0]["key"])
            .values(is_active=False)
        )
    return {"status": "revoked"}
