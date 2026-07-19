from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import BillRow, get_session

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("")
async def list_bills(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BillRow).order_by(BillRow.created_at.desc()))
    rows = list(result.scalars().all())
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "vendor_name": r.vendor_name,
            "invoice_number": r.invoice_number,
            "invoice_date": r.invoice_date,
            "total": r.total,
            "currency": r.currency,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/export.csv")
async def export_csv(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BillRow).order_by(BillRow.created_at.desc()))
    rows = list(result.scalars().all())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "bill_id",
            "case_id",
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "total",
            "currency",
            "status",
            "created_at",
        ]
    )
    for r in rows:
        w.writerow(
            [
                r.id,
                r.case_id or "",
                r.vendor_name,
                r.invoice_number,
                r.invoice_date,
                f"{r.total:.2f}",
                r.currency,
                r.status,
                r.created_at.isoformat() if r.created_at else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clearance-bills.csv"},
    )
