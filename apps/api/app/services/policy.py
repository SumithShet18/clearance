"""Policy retrieval + enforcement. Thresholds/vendors from DB settings when available."""

from __future__ import annotations

from typing import Any

# Defaults when settings not loaded
DEFAULT_KNOWN_VENDORS = {
    "acme supplies",
    "northwind traders",
    "globex industrial",
    "initech services",
    "umbrella logistics",
}

POLICIES = [
    {
        "id": "POL-001",
        "title": "Vendor allowlist",
        "rule": "Invoices from unknown vendors over threshold require human review.",
        "keywords": ["vendor", "unknown", "new"],
    },
    {
        "id": "POL-002",
        "title": "High value threshold",
        "rule": "Any invoice total at or above high-value threshold must escalate.",
        "keywords": ["high", "threshold", "10000"],
    },
    {
        "id": "POL-003",
        "title": "Math integrity",
        "rule": "Line items must sum to subtotal; subtotal + tax must equal total within $0.05.",
        "keywords": ["math", "total", "tax"],
    },
    {
        "id": "POL-004",
        "title": "Duplicate risk",
        "rule": "Same vendor + invoice number already posted is a hold.",
        "keywords": ["duplicate", "invoice number"],
    },
    {
        "id": "POL-005",
        "title": "Currency",
        "rule": "Currencies outside allowlist require treasury review.",
        "keywords": ["currency", "usd", "fx"],
    },
]

# Runtime overrides set by pipeline/settings load
_runtime: dict[str, Any] = {
    "known_vendors": set(DEFAULT_KNOWN_VENDORS),
    "high_value": 10_000.0,
    "unknown_vendor_amount": 500.0,
    "allowed_currencies": {"USD"},
}


def set_runtime_policy(
    *,
    known_vendors: list[str] | None = None,
    high_value: float | None = None,
    unknown_vendor_amount: float | None = None,
    allowed_currencies: list[str] | None = None,
) -> None:
    if known_vendors is not None:
        _runtime["known_vendors"] = {v.strip().lower() for v in known_vendors if v.strip()}
    if high_value is not None:
        _runtime["high_value"] = float(high_value)
    if unknown_vendor_amount is not None:
        _runtime["unknown_vendor_amount"] = float(unknown_vendor_amount)
    if allowed_currencies is not None:
        _runtime["allowed_currencies"] = {c.upper() for c in allowed_currencies if c}


def retrieve_policies(query: str, k: int = 3) -> list[dict]:
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for p in POLICIES:
        score = sum(1 for kw in p["keywords"] if kw in q)
        score += sum(1 for word in p["title"].lower().split() if word in q)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:k] if s > 0] or POLICIES[:k]


def apply_policy(
    vendor: str,
    total: float,
    currency: str,
    *,
    is_duplicate: bool = False,
) -> list[str]:
    issues: list[str] = []
    known = _runtime["known_vendors"]
    high = float(_runtime["high_value"])
    unk = float(_runtime["unknown_vendor_amount"])
    allowed = _runtime["allowed_currencies"]

    if vendor.strip().lower() not in known and total >= unk:
        issues.append(
            f"POL-001: Unknown vendor over ${unk:,.0f} — human review required."
        )
    if total >= high:
        issues.append(
            f"POL-002: High value invoice (>= ${high:,.0f}) — escalate to controller."
        )
    if currency.upper() not in allowed:
        issues.append(
            f"POL-005: Currency {currency} not in allowlist {sorted(allowed)} — treasury review."
        )
    if is_duplicate:
        issues.append(
            "POL-004: Duplicate invoice — same vendor + invoice number already posted."
        )
    return issues
