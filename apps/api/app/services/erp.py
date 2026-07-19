"""Mock ERP writeback — MCP-shaped tool surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class Bill:
    id: str
    vendor_name: str
    invoice_number: str
    total: float
    currency: str
    status: str
    created_at: str


@dataclass
class Anomaly:
    id: str
    bill_id: str
    reason: str
    severity: str
    created_at: str


_BILLS: dict[str, Bill] = {}
_ANOMALIES: dict[str, Anomaly] = {}


def create_bill(
    vendor_name: str,
    invoice_number: str,
    total: float,
    currency: str = "USD",
) -> Bill:
    bill = Bill(
        id=f"BILL-{uuid4().hex[:8].upper()}",
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        total=total,
        currency=currency,
        status="pending_payment",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _BILLS[bill.id] = bill
    return bill


def flag_anomaly(bill_id: str, reason: str, severity: str = "medium") -> dict:
    if bill_id not in _BILLS and not bill_id.startswith("BILL-"):
        # allow flagging pre-create with synthetic id in demos
        pass
    anomaly = Anomaly(
        id=f"ANOM-{uuid4().hex[:8].upper()}",
        bill_id=bill_id,
        reason=reason,
        severity=severity,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _ANOMALIES[anomaly.id] = anomaly
    return asdict(anomaly)


def list_bills() -> list[Bill]:
    return list(_BILLS.values())


def list_anomalies() -> list[Anomaly]:
    return list(_ANOMALIES.values())


def get_bill(bill_id: str) -> Bill | None:
    return _BILLS.get(bill_id)


def reset_erp_state() -> None:
    """Test helper."""
    _BILLS.clear()
    _ANOMALIES.clear()


MCP_TOOLS = [
    {
        "name": "erp_create_bill",
        "description": (
            "Create an accounts-payable bill in the ERP. "
            "Use only after validation and policy checks pass (or human approval). "
            "Required: vendor_name, invoice_number, total. Optional: currency (default USD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "total": {"type": "number"},
                "currency": {"type": "string"},
            },
            "required": ["vendor_name", "invoice_number", "total"],
        },
    },
    {
        "name": "erp_flag_anomaly",
        "description": (
            "Flag a bill or case for fraud/duplicate/policy anomaly review. "
            "Use when POL-001/002/004 risks fire or human notes suspicion. "
            "Required: bill_id, reason. Optional: severity (low|medium|high)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bill_id": {"type": "string"},
                "reason": {"type": "string"},
                "severity": {"type": "string"},
            },
            "required": ["bill_id", "reason"],
        },
    },
    {
        "name": "erp_list_bills",
        "description": "List bills created in this session for audit/demo.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
