from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import dumps, get_or_create_settings, get_session, loads, now
from app.services.policy import set_runtime_policy

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    company_name: str
    known_vendors: list[str]
    high_value_threshold: float
    unknown_vendor_threshold: float
    confidence_hitl_threshold: float
    allowed_currencies: list[str]


class SettingsIn(BaseModel):
    company_name: str | None = None
    known_vendors: list[str] | None = None
    high_value_threshold: float | None = None
    unknown_vendor_threshold: float | None = None
    confidence_hitl_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    allowed_currencies: list[str] | None = None


def _to_out(row) -> SettingsOut:
    return SettingsOut(
        company_name=row.company_name,
        known_vendors=loads(row.known_vendors_json, []),
        high_value_threshold=row.high_value_threshold,
        unknown_vendor_threshold=row.unknown_vendor_threshold,
        confidence_hitl_threshold=row.confidence_hitl_threshold,
        allowed_currencies=loads(row.allowed_currencies_json, ["USD"]),
    )


@router.get("", response_model=SettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)):
    row = await get_or_create_settings(session)
    return _to_out(row)


@router.put("", response_model=SettingsOut)
async def put_settings(body: SettingsIn, session: AsyncSession = Depends(get_session)):
    row = await get_or_create_settings(session)
    if body.company_name is not None:
        row.company_name = body.company_name
    if body.known_vendors is not None:
        row.known_vendors_json = dumps(body.known_vendors)
    if body.high_value_threshold is not None:
        row.high_value_threshold = body.high_value_threshold
    if body.unknown_vendor_threshold is not None:
        row.unknown_vendor_threshold = body.unknown_vendor_threshold
    if body.confidence_hitl_threshold is not None:
        row.confidence_hitl_threshold = body.confidence_hitl_threshold
    if body.allowed_currencies is not None:
        row.allowed_currencies_json = dumps(body.allowed_currencies)
    row.updated_at = now()
    await session.commit()
    await session.refresh(row)
    out = _to_out(row)
    set_runtime_policy(
        known_vendors=out.known_vendors,
        high_value=out.high_value_threshold,
        unknown_vendor_amount=out.unknown_vendor_threshold,
        allowed_currencies=out.allowed_currencies,
    )
    return out
