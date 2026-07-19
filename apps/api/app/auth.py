"""Single-tenant session auth — env password or DB workspace password."""

from __future__ import annotations

from typing import Callable

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.workspace_auth import auth_enabled, verify_password

COOKIE = "clearance_session"
serializer = URLSafeSerializer(settings.session_secret, salt="clearance-auth")


def make_session_token() -> str:
    import secrets

    return serializer.dumps({"ok": True, "n": secrets.token_hex(8)})


def session_valid(token: str | None) -> bool:
    if not auth_enabled():
        return True
    if not token:
        return False
    try:
        data = serializer.loads(token)
        return bool(data.get("ok"))
    except BadSignature:
        return False


def check_password(password: str) -> bool:
    return verify_password(password)


PUBLIC_PREFIXES = (
    "/api/health",
    "/api/auth/",
    "/static/",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not auth_enabled():
            return await call_next(request)

        path = request.url.path
        if path == "/" or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        if path.startswith("/api/"):
            token = request.cookies.get(COOKIE)
            key = request.headers.get("x-clearance-key") or ""
            if session_valid(token) or (key and check_password(key)):
                return await call_next(request)
            return JSONResponse(
                {"detail": "Authentication required. POST /api/auth/login"},
                status_code=401,
            )

        return await call_next(request)
