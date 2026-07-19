"""Invoice extraction: deterministic mock (default) or OpenAI multimodal when configured."""

from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.models.schemas import InvoiceExtraction, LineItem


def extract_invoice(text: str, filename: str = "") -> tuple[InvoiceExtraction, dict[str, Any]]:
    """Return extraction + meta (tokens, cost, mode)."""
    if settings.use_llm:
        try:
            return _extract_llm(text, filename)
        except Exception as exc:  # noqa: BLE001 — fall back for demo reliability
            extraction = _extract_mock(text, filename)
            return extraction, {
                "mode": "mock_fallback",
                "error": str(exc),
                "tokens": 0,
                "cost_usd": 0.0,
            }
    extraction = _extract_mock(text, filename)
    return extraction, {"mode": "mock", "tokens": 0, "cost_usd": 0.0}


def _extract_mock(text: str, filename: str) -> InvoiceExtraction:
    # Prefer sample-tagged blocks if present
    vendor = _first(
        re.findall(r"(?im)^(?:vendor|from|bill from)[:\s]+(.+)$", text)
    ) or _guess_vendor(text, filename)

    invoice_number = _first(
        re.findall(r"(?im)(?:invoice\s*(?:#|no\.?|number)?[:\s]*)([A-Z0-9\-]+)", text)
    ) or "INV-UNKNOWN"

    invoice_date = _first(
        re.findall(r"(?im)(?:invoice\s*date|date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", text)
    ) or ""

    due_date = _first(
        re.findall(r"(?im)(?:due\s*date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", text)
    ) or ""

    currency = _first(re.findall(r"\b(USD|EUR|GBP)\b", text)) or "USD"

    totals = [float(x.replace(",", "")) for x in re.findall(r"(?im)(?:total|amount due)[:\s\$]*([0-9,]+\.\d{2})", text)]
    subtotals = [float(x.replace(",", "")) for x in re.findall(r"(?im)subtotal[:\s\$]*([0-9,]+\.\d{2})", text)]
    taxes = [float(x.replace(",", "")) for x in re.findall(r"(?im)(?:tax|vat)[:\s\$]*([0-9,]+\.\d{2})", text)]

    total = totals[-1] if totals else 0.0
    subtotal = subtotals[-1] if subtotals else (total * 0.92 if total else 0.0)
    tax = taxes[-1] if taxes else max(total - subtotal, 0.0)

    line_items = _parse_line_items(text)
    if not line_items and total:
        line_items = [
            LineItem(
                description="Services / goods (aggregated)",
                quantity=1,
                unit_price=subtotal or total,
                amount=subtotal or total,
                confidence=0.7,
            )
        ]

    # Confidence heuristics: known structure → higher; unknown invoice number → lower
    vendor_conf = 0.95 if vendor and vendor.lower() != "unknown vendor" else 0.55
    inv_conf = 0.92 if invoice_number != "INV-UNKNOWN" else 0.5
    total_conf = 0.93 if total > 0 else 0.4
    date_conf = 0.9 if invoice_date else 0.45

    # Intentionally lower confidence on messy samples
    if "LOWCONF" in text.upper() or "messy" in filename.lower():
        vendor_conf = min(vendor_conf, 0.72)
        inv_conf = min(inv_conf, 0.68)
        total_conf = min(total_conf, 0.7)

    return InvoiceExtraction(
        vendor_name=vendor.strip(),
        vendor_confidence=vendor_conf,
        invoice_number=invoice_number.strip(),
        invoice_number_confidence=inv_conf,
        invoice_date=invoice_date,
        invoice_date_confidence=date_conf,
        due_date=due_date,
        currency=currency,
        subtotal=round(subtotal, 2),
        tax=round(tax, 2),
        total=round(total, 2),
        total_confidence=total_conf,
        line_items=line_items,
        raw_notes="mock extractor (deterministic)",
    )


def _parse_line_items(text: str) -> list[LineItem]:
    items: list[LineItem] = []
    # Format: ITEM | qty | unit | amount
    for m in re.finditer(
        r"(?m)^[-*]\s*(.+?)\s+\|\s*([\d.]+)\s+\|\s*([\d.,]+)\s+\|\s*([\d.,]+)\s*$",
        text,
    ):
        desc, qty, unit, amt = m.groups()
        items.append(
            LineItem(
                description=desc.strip(),
                quantity=float(qty),
                unit_price=float(unit.replace(",", "")),
                amount=float(amt.replace(",", "")),
                confidence=0.9,
            )
        )
    return items


def _guess_vendor(text: str, filename: str) -> str:
    for line in text.splitlines()[:8]:
        line = line.strip()
        if not line or line.lower().startswith(("invoice", "date", "bill to", "ship")):
            continue
        if len(line) > 3:
            return line
    stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
    return stem or "Unknown Vendor"


def _first(items: list[str]) -> str:
    return items[0] if items else ""


def _extract_llm(text: str, filename: str) -> tuple[InvoiceExtraction, dict[str, Any]]:
    """Optional OpenAI path — structured JSON. Requires OPENAI_API_KEY."""
    import json
    import urllib.request

    prompt = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract invoice fields as JSON with keys: vendor_name, invoice_number, "
                    "invoice_date, due_date, currency, subtotal, tax, total, line_items "
                    "(list of {description, quantity, unit_price, amount}), and confidences "
                    "vendor_confidence, invoice_number_confidence, invoice_date_confidence, "
                    "total_confidence (0-1). Return JSON only."
                ),
            },
            {"role": "user", "content": f"Filename: {filename}\n\n{text[:12000]}"},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(prompt).encode(),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 — explicit OpenAI API
        body = json.loads(resp.read().decode())
    content = body["choices"][0]["message"]["content"]
    data = json.loads(content)
    usage = body.get("usage", {})
    tokens = int(usage.get("total_tokens", 0))
    # rough cost estimate for gpt-4o-mini
    cost = tokens * 0.0000003

    lines = [
        LineItem(
            description=str(li.get("description", "")),
            quantity=float(li.get("quantity", 1) or 1),
            unit_price=float(li.get("unit_price", 0) or 0),
            amount=float(li.get("amount", 0) or 0),
            confidence=float(li.get("confidence", 0.85) or 0.85),
        )
        for li in data.get("line_items", []) or []
    ]
    extraction = InvoiceExtraction(
        vendor_name=str(data.get("vendor_name", "")),
        vendor_confidence=float(data.get("vendor_confidence", 0.8)),
        invoice_number=str(data.get("invoice_number", "")),
        invoice_number_confidence=float(data.get("invoice_number_confidence", 0.8)),
        invoice_date=str(data.get("invoice_date", "")),
        invoice_date_confidence=float(data.get("invoice_date_confidence", 0.8)),
        due_date=str(data.get("due_date", "")),
        currency=str(data.get("currency", "USD")),
        subtotal=float(data.get("subtotal", 0) or 0),
        tax=float(data.get("tax", 0) or 0),
        total=float(data.get("total", 0) or 0),
        total_confidence=float(data.get("total_confidence", 0.8)),
        line_items=lines,
        raw_notes="llm extractor",
    )
    return extraction, {"mode": "llm", "tokens": tokens, "cost_usd": cost}
