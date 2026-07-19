from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter, Query

from app.models.schemas import EvalRunResult, InvoiceExtraction
from app.services.extractor import extract_invoice
from app.services.pipeline import overall_confidence, validate_extraction

router = APIRouter(prefix="/api/evals", tags=["evals"])


def _root() -> Path:
    return Path(__file__).resolve().parents[4]


def _iter_gold_files() -> list[Path]:
    gold = _root() / "evals" / "gold"
    files = list(gold.glob("*.json"))
    syn = gold / "synthetic"
    if syn.exists():
        files.extend(sorted(syn.glob("*.json")))
    return files


@router.get("/run", response_model=EvalRunResult)
async def run_gold_eval(include_synthetic: bool = Query(True)):
    """Offline eval harness — field match rates on gold set (+ synthetic if present)."""
    details = []
    vendor_hits = total_hits = field_hits = field_total = 0
    cases = 0

    files = _iter_gold_files() if include_synthetic else list((_root() / "evals" / "gold").glob("*.json"))
    for path in files:
        gold = json.loads(path.read_text(encoding="utf-8"))
        sample_path = _root() / "samples" / gold["sample"]
        if not sample_path.exists():
            continue
        text = sample_path.read_text(encoding="utf-8")
        pred, _meta = extract_invoice(text, gold["sample"])
        expected = InvoiceExtraction(**{k: v for k, v in gold["expected"].items() if k in InvoiceExtraction.model_fields})
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
        details=details[:100],  # cap response size
    )


@router.get("/benchmark")
async def run_benchmark(
    source: str = Query("synthetic"),
    limit: int = Query(50, ge=1, le=200),
):
    """Clearance Bench: per-field accuracy on synthetic (or manual/cord) corpus."""
    root = _root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from evals.run_benchmark import load_golds, run_extract_bench, write_report

    if source == "synthetic":
        syn = root / "evals" / "gold" / "synthetic"
        if not syn.exists() or not list(syn.glob("*.json")):
            from evals.datasets.synthetic import generate_corpus

            generate_corpus(50)

    golds = load_golds(source, limit)
    if not golds:
        return {"error": "no golds", "cases": 0}
    result = run_extract_bench(golds)
    write_report(result, None)
    return {
        "source": source,
        "cases": result["cases"],
        "micro_field_accuracy": result["micro_field_accuracy"],
        "per_field": result["per_field"],
    }
