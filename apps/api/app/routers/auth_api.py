from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.auth import COOKIE, check_password, make_session_token, session_valid
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    password: str = ""


@router.get("/status")
async def auth_status():
    import os

    # Safe diagnostics (never return the password value)
    raw = os.environ.get("CLEARANCE_PASSWORD")
    return {
        "auth_required": settings.auth_required,
        "demo_mode": settings.clearance_demo,
        "product": "Clearance",
        "password_env_present": raw is not None,
        "password_env_nonempty": bool(raw and str(raw).strip()),
        "hint": (
            "CLEARANCE_PASSWORD is missing or empty on this process. "
            "In Render: Environment → set CLEARANCE_PASSWORD → Save → Manual Deploy → Clear build cache if needed."
            if not settings.auth_required
            else "Login required — open the site and sign in"
        ),
    }


@router.get("/me")
async def auth_me(request: Request):
    """Public session probe (not gated). UI uses this to show login vs app."""
    if not settings.auth_required:
        return {
            "auth_required": False,
            "logged_in": True,
            "mode": "open",
        }
    token = request.cookies.get(COOKIE)
    ok = session_valid(token)
    return {
        "auth_required": True,
        "logged_in": ok,
        "mode": "password",
    }


@router.post("/login")
async def login(body: LoginBody, response: Response):
    if not settings.auth_required:
        return {"ok": True, "auth_required": False, "detail": "Open access — no password configured"}
    if not check_password(body.password):
        response.status_code = 401
        return {"ok": False, "detail": "Invalid password"}
    token = make_session_token()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
        path="/",
    )
    return {"ok": True, "auth_required": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
