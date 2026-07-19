"""Clearance Bench unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from evals.datasets.schema import GoldInvoice, field_scores  # noqa: E402
from evals.datasets.synthetic import generate_corpus, load_synthetic_golds  # noqa: E402
from evals.run_benchmark import run_extract_bench  # noqa: E402


def test_field_scores_total_tolerance():
    g = GoldInvoice(
        id="t1",
        source="manual",
        sample_path="x",
        vendor_name="ACME Supplies",
        invoice_number="INV-1",
        total=100.0,
        currency="USD",
    )
    pred = {"vendor_name": "ACME Supplies", "invoice_number": "INV-1", "total": 100.02, "currency": "USD"}
    s = field_scores(pred, g)
    assert s["total"] is True
    assert s["vendor"] is True


def test_synthetic_generate_and_extract_accuracy():
    generate_corpus(12, seed=7)
    golds = load_synthetic_golds(12)
    assert len(golds) == 12
    result = run_extract_bench(golds)
    assert result["cases"] == 12
    assert result["micro_field_accuracy"] >= 0.95
