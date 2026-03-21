"""
auth.py — API key authentication middleware.

Accepts the key two ways:
  1. Header:  Authorization: Bearer hb_live_...   (all normal fetch() calls)
  2. Query:   ?api_key=hb_live_...                (EventSource / SSE — browsers
                                                   cannot send headers with EventSource)

Public routes (no auth needed): /health, /docs, /openapi.json, /auth/register
OPTIONS preflight requests are always allowed through (required for CORS).
"""
from core.database import get_tenant_by_key
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc",
                "/auth/register", "/auth/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Always pass OPTIONS through — these are CORS preflight requests.
        # The browser sends OPTIONS before every cross-origin request to check
        # permissions. Blocking them with 401 prevents CORS from working at all.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Always allow public routes
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        # 1. Try Authorization header (standard fetch calls)
        api_key = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()

        # 2. Fall back to query param (needed for EventSource which can't set headers)
        if not api_key:
            api_key = request.query_params.get("api_key", "").strip()

        if not api_key:
            raise HTTPException(
                401,
                "Missing API key. "
                "Send header: Authorization: Bearer hb_live_... "
                "or query param: ?api_key=hb_live_..."
            )

        tenant = get_tenant_by_key(api_key)
        if not tenant:
            raise HTTPException(401, "Invalid or inactive API key")

        request.state.tenant = tenant
        return await call_next(request)
