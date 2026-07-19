"""Offline gold eval — run from apps/api with PYTHONPATH=. or via pytest path hacks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from app.services.extractor import extract_invoice  # noqa: E402
from app.services.pipeline import overall_confidence, validate_extraction  # noqa: E402


def test_gold_field_accuracy_reasonable():
    gold_dir = ROOT / "evals" / "gold"
    samples = ROOT / "samples"
    field_hits = field_total = 0
    cases = 0

    for path in sorted(gold_dir.glob("*.json")):
        gold = json.loads(path.read_text(encoding="utf-8"))
        text = (samples / gold["sample"]).read_text(encoding="utf-8")
        pred, _ = extract_invoice(text, gold["sample"])
        exp = gold["expected"]
        cases += 1
        checks = [
            pred.vendor_name.strip().lower() == exp["vendor_name"].strip().lower(),
            abs(pred.total - float(exp["total"])) <= 0.05,
            pred.invoice_number.strip().upper() == exp["invoice_number"].strip().upper(),
            pred.currency.upper() == exp["currency"].upper(),
        ]
        for ok in checks:
            field_total += 1
            if ok:
                field_hits += 1
        assert overall_confidence(pred) > 0
        # validation may fail on policy — that's OK; extraction should still parse
        validate_extraction(pred)

    accuracy = field_hits / field_total if field_total else 0
    assert cases >= 4
    assert accuracy >= 0.75, f"field accuracy too low: {accuracy:.2%} ({field_hits}/{field_total})"


def test_clean_acme_auto_path_signals():
    text = (ROOT / "samples" / "invoice_acme_clean.txt").read_text(encoding="utf-8")
    pred, meta = extract_invoice(text, "invoice_acme_clean.txt")
    assert pred.vendor_name.lower().startswith("acme")
    assert pred.total == 1063.8
    assert meta["mode"] in {"mock", "mock_fallback", "llm"}
