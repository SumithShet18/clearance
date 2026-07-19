from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.auth import COOKIE, check_password, make_session_token
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    password: str = ""


@router.get("/status")
async def auth_status():
    return {
        "auth_required": settings.auth_required,
        "demo_mode": settings.clearance_demo,
        "product": "Clearance",
    }


@router.post("/login")
async def login(body: LoginBody, response: Response):
    if not settings.auth_required:
        return {"ok": True, "auth_required": False}
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
