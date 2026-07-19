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


def test_synthetic_generate_and_extract_accuracy(tmp_path, monkeypatch):
    # Isolate corpus so we never shrink the committed 50-doc bench set
    monkeypatch.chdir(tmp_path)
    # Point synthetic module root via writing under real paths is hard;
    # instead only load existing committed golds (preferred for CI).
    golds = load_synthetic_golds(20)
    if len(golds) < 10:
        generate_corpus(20, seed=7)
        golds = load_synthetic_golds(20)
    assert len(golds) >= 10
    result = run_extract_bench(golds)
    assert result["cases"] >= 10
    assert result["micro_field_accuracy"] >= 0.95


def test_sroie_hard_strips_assist_footer():
    from evals.datasets.sroie_loader import load_sroie, strip_assist_footer

    sample = (
        "ACME STORE\nTOTAL: 12.50\n"
        "Vendor: ACME STORE\nInvoice Number: SROIE-99\nInvoice Date: 01/01/2020\n"
        "Currency: USD\nAddress: 1 Main\nTotal: 12.50\n"
    )
    body = strip_assist_footer(sample)
    assert "Vendor: ACME STORE" not in body
    assert "Invoice Number: SROIE-99" not in body
    assert "TOTAL: 12.50" in body

    hard = load_sroie(limit=5, cache=True, ocr_only=True)
    if not hard:
        hard = load_sroie(limit=5, cache=False, ocr_only=True)
    assert len(hard) >= 1
    path = ROOT / hard[0].sample_path
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Invoice Number: SROIE-" not in text
    # Hard track is intentionally harder than assisted — just smoke that it runs
    result = run_extract_bench(hard)
    assert result["cases"] >= 1
    assert 0.0 <= result["micro_field_accuracy"] <= 1.0
