from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import CaseRow, get_case, get_session, list_cases, loads, new_id, now
from app.models.schemas import (
    CaseCreateResponse,
    CaseDetail,
    CaseStatus,
    CaseSummary,
    Decision,
    InvoiceExtraction,
    MetricsResponse,
    ProgressLedger,
    ReviewAction,
    TaskLedger,
    ValidationResult,
)
from app.services.ingest import load_upload
from app.services.pipeline import apply_review, run_pipeline

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _row_to_summary(row: CaseRow) -> CaseSummary:
    ext = loads(row.extraction_json, {})
    return CaseSummary(
        id=row.id,
        filename=row.filename,
        status=CaseStatus(row.status),
        vendor_name=ext.get("vendor_name"),
        total=ext.get("total"),
        overall_confidence=row.overall_confidence,
        decision=Decision(row.decision) if row.decision else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        cost_usd=row.cost_usd or 0.0,
    )


def _normalize_steps(raw: list) -> list[dict]:
    out: list[dict] = []
    for s in raw or []:
        if isinstance(s, dict):
            out.append(s)
        elif isinstance(s, str) and s.startswith("name="):
            continue
    return out


def _row_to_detail(row: CaseRow) -> CaseDetail:
    ext_raw = loads(row.extraction_json, {})
    val_raw = loads(row.validation_json, {})
    steps = _normalize_steps(loads(row.steps_json, []))
    task = loads(row.task_ledger_json, {})
    progress = loads(row.progress_ledger_json, {})
    audit = loads(row.audit_json, [])
    if isinstance(audit, str):
        audit = []
    base = _row_to_summary(row)
    return CaseDetail(
        **base.model_dump(),
        extraction=InvoiceExtraction(**ext_raw) if ext_raw else None,
        validation=ValidationResult(**val_raw) if val_raw else None,
        steps=steps,
        task_ledger=TaskLedger(**task) if task else None,
        progress_ledger=ProgressLedger(**progress) if progress else None,
        erp_bill_id=row.erp_bill_id,
        audit=audit if isinstance(audit, list) else [],
        content_preview=(row.content_text or "")[:2000],
    )


@router.get("", response_model=list[CaseSummary])
async def get_cases(
    status: str | None = Query(None),
    q: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_cases(session, status=status, q=q)
    return [_row_to_summary(r) for r in rows]


@router.get("/metrics/summary", response_model=MetricsResponse)
async def metrics(session: AsyncSession = Depends(get_session)):
    rows = await list_cases(session)
    total = len(rows)
    auto_resolved = sum(
        1
        for r in rows
        if r.status == CaseStatus.acted.value and "human_approve" not in (r.audit_json or "")
    )
    needs = sum(1 for r in rows if r.status == CaseStatus.needs_review.value)
    acted = sum(1 for r in rows if r.status == CaseStatus.acted.value)
    confs = [r.overall_confidence for r in rows if r.overall_confidence is not None]
    costs = [r.cost_usd or 0 for r in rows]
    return MetricsResponse(
        total_cases=total,
        auto_resolved=auto_resolved,
        needs_review=needs,
        acted=acted,
        auto_resolve_rate=(auto_resolved / total) if total else 0.0,
        avg_confidence=(sum(confs) / len(confs)) if confs else 0.0,
        avg_cost_usd=(sum(costs) / len(costs)) if costs else 0.0,
        gold_eval=None,
    )


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case_detail(case_id: str, session: AsyncSession = Depends(get_session)):
    row = await get_case(session, case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    return _row_to_detail(row)


@router.post("", response_model=CaseCreateResponse)
async def create_case(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    raw = await file.read()
    filename = file.filename or "upload.txt"
    case_id = new_id()
    dest = Path(settings.upload_dir) / f"{case_id}_{filename}"
    dest.write_bytes(raw)

    text, meta, is_image = load_upload(dest, filename, raw)
    if is_image:
        from app.services.extractor import extract_from_image

        ext, vmeta = extract_from_image(str(dest), filename)
        meta = {**meta, **vmeta}
        text = (
            f"Vendor: {ext.vendor_name}\n"
            f"Invoice Number: {ext.invoice_number}\n"
            f"Invoice Date: {ext.invoice_date}\n"
            f"Currency: {ext.currency}\n"
            f"Subtotal: {ext.subtotal:.2f}\n"
            f"Tax: {ext.tax:.2f}\n"
            f"Total: {ext.total:.2f}\n"
            f"# vision_meta={vmeta.get('mode')}\n"
            f"# notes={ext.raw_notes}\n"
        )

    row = CaseRow(
        id=case_id,
        filename=filename,
        status=CaseStatus.pending.value,
        content_text=text,
        file_path=str(dest),
        created_at=now(),
        updated_at=now(),
        archived=0,
    )
    session.add(row)
    await session.commit()

    await run_pipeline(session, row)
    await session.refresh(row)

    return CaseCreateResponse(id=row.id, status=CaseStatus(row.status), filename=row.filename)


@router.post("/from-sample/{sample_name:path}", response_model=CaseCreateResponse)
async def create_from_sample(sample_name: str, session: AsyncSession = Depends(get_session)):
    root = Path(__file__).resolve().parents[4] / "samples"
    path = (root / sample_name).resolve()
    if not str(path).startswith(str(root.resolve())) or not path.exists():
        raise HTTPException(404, f"Sample not found: {sample_name}")
    text = path.read_text(encoding="utf-8")
    case_id = new_id()
    row = CaseRow(
        id=case_id,
        filename=sample_name,
        status=CaseStatus.pending.value,
        content_text=text,
        file_path=str(path),
        created_at=now(),
        updated_at=now(),
        archived=0,
    )
    session.add(row)
    await session.commit()
    await run_pipeline(session, row)
    await session.refresh(row)
    return CaseCreateResponse(id=row.id, status=CaseStatus(row.status), filename=row.filename)


@router.post("/{case_id}/review", response_model=CaseDetail)
async def review_case(
    case_id: str,
    body: ReviewAction,
    session: AsyncSession = Depends(get_session),
):
    row = await get_case(session, case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    if row.status != CaseStatus.needs_review.value:
        raise HTTPException(400, f"Case is not awaiting review (status={row.status})")
    if body.action not in {"approve", "reject", "edit_and_approve"}:
        raise HTTPException(400, "action must be approve | reject | edit_and_approve")
    row = await apply_review(session, row, body.action, body.extraction, body.note)
    await session.refresh(row)
    return _row_to_detail(row)


@router.post("/{case_id}/archive")
async def archive_case(case_id: str, session: AsyncSession = Depends(get_session)):
    row = await get_case(session, case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    row.archived = 1
    row.updated_at = now()
    await session.commit()
    return {"id": case_id, "archived": True}


@router.get("/{case_id}/traces")
async def case_traces(case_id: str, session: AsyncSession = Depends(get_session)):
    row = await get_case(session, case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    from app.services.traces import read_spans

    spans = read_spans(case_id)
    return {"case_id": case_id, "spans": spans, "count": len(spans)}


@router.get("/{case_id}/export")
async def export_case(case_id: str, session: AsyncSession = Depends(get_session)):
    row = await get_case(session, case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    detail = _row_to_detail(row)
    return {
        "case_id": row.id,
        "exported_at": now().isoformat(),
        "product": "Clearance",
        "version": "1.0.0",
        "filename": row.filename,
        "status": row.status,
        "decision": row.decision,
        "erp_bill_id": row.erp_bill_id,
        "overall_confidence": row.overall_confidence,
        "cost_usd": row.cost_usd,
        "extraction": detail.extraction.model_dump() if detail.extraction else None,
        "validation": detail.validation.model_dump() if detail.validation else None,
        "task_ledger": detail.task_ledger.model_dump() if detail.task_ledger else None,
        "progress_ledger": detail.progress_ledger.model_dump() if detail.progress_ledger else None,
        "steps": detail.steps,
        "audit": detail.audit,
    }
