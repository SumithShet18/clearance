from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class CaseRow(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    content_text: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    extraction_json: Mapped[str] = mapped_column(Text, default="{}")
    validation_json: Mapped[str] = mapped_column(Text, default="{}")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    task_ledger_json: Mapped[str] = mapped_column(Text, default="{}")
    progress_ledger_json: Mapped[str] = mapped_column(Text, default="{}")
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    erp_bill_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    audit_json: Mapped[str] = mapped_column(Text, default="[]")
    archived: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BillRow(Base):
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vendor_name: Mapped[str] = mapped_column(String(512), default="")
    invoice_number: Mapped[str] = mapped_column(String(256), default="")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    invoice_date: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AppSettingsRow(Base):
    """Singleton-style settings (id=1)."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    known_vendors_json: Mapped[str] = mapped_column(Text, default="[]")
    high_value_threshold: Mapped[float] = mapped_column(Float, default=10_000.0)
    unknown_vendor_threshold: Mapped[float] = mapped_column(Float, default=500.0)
    confidence_hitl_threshold: Mapped[float] = mapped_column(Float, default=0.85)
    allowed_currencies_json: Mapped[str] = mapped_column(Text, default='["USD"]')
    company_name: Mapped[str] = mapped_column(String(256), default="My Company")
    # sha256 hex of workspace password (empty = open unless CLEARANCE_PASSWORD env)
    workspace_password_hash: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # lightweight migrations for older DBs
        for stmt in (
            "ALTER TABLE cases ADD COLUMN archived INTEGER DEFAULT 0",
            "ALTER TABLE app_settings ADD COLUMN workspace_password_hash VARCHAR(128) DEFAULT ''",
        ):
            try:
                await conn.execute(__import__("sqlalchemy").text(stmt))
            except Exception:  # noqa: BLE001 — column may already exist
                pass

    # Load workspace password hash into memory for auth middleware
    from app.workspace_auth import set_db_password_hash

    async with SessionLocal() as session:
        row = await session.get(AppSettingsRow, 1)
        if row is not None:
            set_db_password_hash(getattr(row, "workspace_password_hash", "") or "")


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


def _to_jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def dumps(obj: Any) -> str:
    return json.dumps(_to_jsonable(obj), default=str)


def loads(raw: str, default: Any) -> Any:
    if not raw:
        return default
    return json.loads(raw)


async def list_cases(
    session: AsyncSession,
    *,
    status: str | None = None,
    q: str | None = None,
    include_archived: bool = False,
) -> list[CaseRow]:
    stmt = select(CaseRow).order_by(CaseRow.created_at.desc())
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    out: list[CaseRow] = []
    qn = (q or "").strip().lower()
    for r in rows:
        if not include_archived and getattr(r, "archived", 0):
            continue
        if status and r.status != status:
            continue
        if qn:
            blob = f"{r.filename} {r.extraction_json} {r.erp_bill_id or ''}".lower()
            if qn not in blob:
                continue
        out.append(r)
    return out


async def get_case(session: AsyncSession, case_id: str) -> CaseRow | None:
    return await session.get(CaseRow, case_id)


async def get_or_create_settings(session: AsyncSession) -> AppSettingsRow:
    row = await session.get(AppSettingsRow, 1)
    if row:
        return row
    row = AppSettingsRow(
        id=1,
        known_vendors_json=json.dumps(
            [
                "ACME Supplies",
                "Northwind Traders",
                "Globex Industrial",
                "Initech Services",
                "Umbrella Logistics",
            ]
        ),
        high_value_threshold=settings.high_value_threshold,
        unknown_vendor_threshold=settings.unknown_vendor_threshold,
        confidence_hitl_threshold=settings.confidence_hitl_threshold,
        allowed_currencies_json=json.dumps(["USD"]),
        company_name="My Company",
        workspace_password_hash="",
        updated_at=now(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
