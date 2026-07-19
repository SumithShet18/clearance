"""Unified gold schema + field scoring for Clearance Bench."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GoldInvoice(BaseModel):
    id: str
    source: str  # synthetic | cord | manual
    sample_path: str
    vendor_name: str
    invoice_number: str = ""
    invoice_date: str = ""
    total: float = 0.0
    currency: str = "USD"
    tax: float | None = None
    subtotal: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


def normalize_text(s: str) -> str:
    return " ".join((s or "").lower().split())


def totals_match(a: float, b: float, tol: float = 0.05) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def field_scores(pred: dict[str, Any], gold: GoldInvoice) -> dict[str, bool]:
    inv_ok = True
    if gold.invoice_number:
        inv_ok = normalize_text(str(pred.get("invoice_number", ""))) == normalize_text(
            gold.invoice_number
        )
    return {
        "vendor": normalize_text(str(pred.get("vendor_name", "")))
        == normalize_text(gold.vendor_name),
        "invoice_number": inv_ok,
        "total": totals_match(float(pred.get("total") or 0), gold.total),
        "currency": str(pred.get("currency", "USD")).upper() == gold.currency.upper(),
    }
