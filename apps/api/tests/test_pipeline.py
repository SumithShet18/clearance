import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import InvoiceExtraction, LineItem
from app.services.extractor import extract_invoice
from app.services.pipeline import decide, overall_confidence, validate_extraction
from app.models.schemas import Decision


def test_acme_extract():
    root = Path(__file__).resolve().parents[3]
    text = (root / "samples" / "invoice_acme_clean.txt").read_text(encoding="utf-8")
    ext, meta = extract_invoice(text, "invoice_acme_clean.txt")
    assert ext.total == 1063.8
    assert "acme" in ext.vendor_name.lower()
    assert meta["mode"] == "mock"


def test_validation_math():
    ext = InvoiceExtraction(
        vendor_name="ACME Supplies",
        invoice_number="INV-1",
        total=100,
        subtotal=90,
        tax=10,
        currency="USD",
        vendor_confidence=0.9,
        invoice_number_confidence=0.9,
        invoice_date_confidence=0.9,
        total_confidence=0.9,
        line_items=[LineItem(description="x", amount=90, confidence=0.9)],
    )
    v = validate_extraction(ext)
    assert v.math_ok
    assert v.schema_ok


def test_decide_low_confidence_escalates():
    ext = InvoiceExtraction(
        vendor_name="ACME Supplies",
        invoice_number="INV-1",
        total=100,
        subtotal=90,
        tax=10,
        currency="USD",
        vendor_confidence=0.5,
        invoice_number_confidence=0.5,
        invoice_date_confidence=0.5,
        total_confidence=0.5,
    )
    v = validate_extraction(ext)
    conf = overall_confidence(ext)
    decision, _reason, needs = decide(ext, v, conf)
    assert needs
    assert decision in {Decision.escalate, Decision.hold}
