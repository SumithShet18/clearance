from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.models.schemas import EvalRunResult, InvoiceExtraction
from app.services.extractor import extract_invoice
from app.services.pipeline import overall_confidence, validate_extraction

router = APIRouter(prefix="/api/evals", tags=["evals"])


def _gold_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "evals" / "gold"


@router.get("/run", response_model=EvalRunResult)
async def run_gold_eval():
    """Offline eval harness — field match rates on gold set."""
    gold_dir = _gold_dir()
    details = []
    vendor_hits = total_hits = field_hits = field_total = 0
    cases = 0

    for path in sorted(gold_dir.glob("*.json")):
        gold = json.loads(path.read_text(encoding="utf-8"))
        sample_path = Path(__file__).resolve().parents[4] / "samples" / gold["sample"]
        if not sample_path.exists():
            continue
        text = sample_path.read_text(encoding="utf-8")
        pred, _meta = extract_invoice(text, gold["sample"])
        expected = InvoiceExtraction(**gold["expected"])
        cases += 1

        vendor_ok = pred.vendor_name.strip().lower() == expected.vendor_name.strip().lower()
        total_ok = abs(pred.total - expected.total) <= 0.05
        inv_ok = pred.invoice_number.strip().upper() == expected.invoice_number.strip().upper()
        currency_ok = pred.currency.upper() == expected.currency.upper()

        for ok in (vendor_ok, total_ok, inv_ok, currency_ok):
            field_total += 1
            if ok:
                field_hits += 1
        if vendor_ok:
            vendor_hits += 1
        if total_ok:
            total_hits += 1

        validation = validate_extraction(pred)
        details.append(
            {
                "sample": gold["sample"],
                "vendor_ok": vendor_ok,
                "total_ok": total_ok,
                "invoice_number_ok": inv_ok,
                "pred_total": pred.total,
                "expected_total": expected.total,
                "confidence": overall_confidence(pred),
                "validation_ok": validation.ok,
            }
        )

    return EvalRunResult(
        cases=cases,
        field_accuracy=(field_hits / field_total) if field_total else 0.0,
        total_match_rate=(total_hits / cases) if cases else 0.0,
        vendor_match_rate=(vendor_hits / cases) if cases else 0.0,
        details=details,
    )
