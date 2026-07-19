from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import COOKIE, check_password, make_session_token, session_valid
from app.config import settings
from app.db import get_or_create_settings, get_session, now
from app.workspace_auth import (
    auth_enabled,
    env_password,
    get_db_password_hash,
    hash_password,
    password_source,
    set_db_password_hash,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    password: str = ""


class SetupBody(BaseModel):
    password: str = Field(min_length=4, max_length=128)


@router.get("/status")
async def auth_status():
    raw = os.environ.get("CLEARANCE_PASSWORD")
    enabled = auth_enabled()
    src = password_source()
    return {
        "auth_required": enabled,
        "demo_mode": settings.clearance_demo,
        "product": "Clearance",
        "password_source": src,
        "password_env_present": raw is not None,
        "password_env_nonempty": bool(raw and str(raw).strip()),
        "workspace_password_set": bool(get_db_password_hash()),
        "can_setup_in_ui": not enabled,
        "hint": (
            "Open access. Use Settings → Set workspace password (works without Render env), "
            "or set CLEARANCE_PASSWORD on the host."
            if not enabled
            else f"Login required (source={src}). Open the site and sign in."
        ),
    }


@router.get("/me")
async def auth_me(request: Request):
    if not auth_enabled():
        return {
            "auth_required": False,
            "logged_in": True,
            "mode": "open",
            "can_setup_in_ui": True,
        }
    token = request.cookies.get(COOKIE)
    ok = session_valid(token)
    return {
        "auth_required": True,
        "logged_in": ok,
        "mode": "password",
        "password_source": password_source(),
        "can_setup_in_ui": False,
    }


@router.post("/setup")
async def setup_password(
    body: SetupBody,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """
    First-time password from UI when nothing is configured yet.
    Does not require env CLEARANCE_PASSWORD (works on Render free tier).
    """
    if env_password():
        response.status_code = 400
        return {
            "ok": False,
            "detail": "CLEARANCE_PASSWORD env already set — use that password to log in.",
        }
    if get_db_password_hash():
        response.status_code = 400
        return {
            "ok": False,
            "detail": "Workspace password already set. Log in, then change it in Settings.",
        }
    pwd = body.password.strip()
    if len(pwd) < 4:
        response.status_code = 400
        return {"ok": False, "detail": "Password must be at least 4 characters"}

    row = await get_or_create_settings(session)
    h = hash_password(pwd)
    row.workspace_password_hash = h
    row.updated_at = now()
    await session.commit()
    set_db_password_hash(h)

    token = make_session_token()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
        path="/",
    )
    return {
        "ok": True,
        "auth_required": True,
        "detail": "Workspace password set. You are signed in.",
    }


@router.post("/set-password")
async def change_password(
    body: SetupBody,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Change workspace password when open or already logged in (not when env-only)."""
    if env_password():
        response.status_code = 400
        return {
            "ok": False,
            "detail": "Password is controlled by CLEARANCE_PASSWORD env — change it on the host.",
        }
    # If auth already on, require session
    if auth_enabled() and not session_valid(request.cookies.get(COOKIE)):
        response.status_code = 401
        return {"ok": False, "detail": "Sign in first to change password"}

    pwd = body.password.strip()
    if len(pwd) < 4:
        response.status_code = 400
        return {"ok": False, "detail": "Password must be at least 4 characters"}

    row = await get_or_create_settings(session)
    h = hash_password(pwd)
    row.workspace_password_hash = h
    row.updated_at = now()
    await session.commit()
    set_db_password_hash(h)

    token = make_session_token()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
        path="/",
    )
    return {"ok": True, "auth_required": True, "detail": "Password updated"}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    if not auth_enabled():
        return {
            "ok": True,
            "auth_required": False,
            "detail": "Open access — set a password in Settings to enable login",
        }
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
