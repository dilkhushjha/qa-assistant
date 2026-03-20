"""
auth.py — API key authentication.

Clients send:  Authorization: Bearer hb_live_xxxx
The middleware resolves the tenant and injects it into request.state.tenant.

Public routes (no auth): /health, /docs, /openapi.json, /auth/register
"""
# ── sys.path fix ──
from core.database import get_tenant_by_key
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
import sys as _sys
import os as _os
_BACKEND_DIR = _os.path.abspath(__file__)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)
# ── sys.path fix ──


PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc",
                "/auth/register", "/auth/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                401, "Missing API key. Send: Authorization: Bearer hb_live_...")

        api_key = auth_header[7:].strip()
        tenant = get_tenant_by_key(api_key)
        if not tenant:
            raise HTTPException(401, "Invalid or inactive API key")

        request.state.tenant = tenant
        return await call_next(request)
