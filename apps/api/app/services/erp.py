"""Mock ERP writeback — MCP-shaped tool surface for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass, field
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


_BILLS: dict[str, Bill] = {}


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


def list_bills() -> list[Bill]:
    return list(_BILLS.values())


def get_bill(bill_id: str) -> Bill | None:
    return _BILLS.get(bill_id)


# MCP-style tool descriptors (documentation + future MCP server wiring)
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
        "name": "erp_list_bills",
        "description": "List bills created in this session for audit/demo.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
