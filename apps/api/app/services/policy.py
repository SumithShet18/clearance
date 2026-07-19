"""Simple policy RAG stand-in for demo (no vector DB required in Phase 1)."""

from __future__ import annotations

POLICIES = [
    {
        "id": "POL-001",
        "title": "Vendor allowlist",
        "rule": "Invoices from unknown vendors over $500 require human review.",
        "keywords": ["vendor", "unknown", "new"],
    },
    {
        "id": "POL-002",
        "title": "High value threshold",
        "rule": "Any invoice total >= $10,000 must escalate to finance controller.",
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
        "rule": "Same vendor + invoice number within 90 days is a hold.",
        "keywords": ["duplicate", "invoice number"],
    },
    {
        "id": "POL-005",
        "title": "Currency",
        "rule": "Non-USD invoices require treasury review before ERP writeback.",
        "keywords": ["currency", "usd", "fx"],
    },
]

KNOWN_VENDORS = {
    "acme supplies",
    "northwind traders",
    "globex industrial",
    "initech services",
    "umbrella logistics",
}


def retrieve_policies(query: str, k: int = 3) -> list[dict]:
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for p in POLICIES:
        score = sum(1 for kw in p["keywords"] if kw in q)
        score += sum(1 for word in p["title"].lower().split() if word in q)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:k] if s > 0] or POLICIES[:k]


def apply_policy(vendor: str, total: float, currency: str) -> list[str]:
    issues: list[str] = []
    if vendor.strip().lower() not in KNOWN_VENDORS and total >= 500:
        issues.append("POL-001: Unknown vendor over $500 — human review required.")
    if total >= 10_000:
        issues.append("POL-002: High value invoice — escalate to controller.")
    if currency.upper() != "USD":
        issues.append("POL-005: Non-USD currency — treasury review required.")
    return issues
