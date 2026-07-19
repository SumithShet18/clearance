#!/usr/bin/env python3
"""
Clearance ERP MCP server (stdio).

Exposes the same tools as the in-process ERP mock so agents can connect via MCP:
  - erp_create_bill
  - erp_flag_anomaly
  - erp_list_bills

Run:
  python mcp-servers/erp/server.py

Protocol: minimal JSON-RPC over stdin/stdout compatible with MCP tool listing demos.
For full MCP SDK, swap transport; tool contracts stay identical to GET /api/tools.
"""

from __future__ import annotations

import json
import sys
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


BILLS: dict[str, Bill] = {}
ANOMALIES: list[dict] = []

TOOLS = [
    {
        "name": "erp_create_bill",
        "description": "Create AP bill after validation/HITL. Args: vendor_name, invoice_number, total, currency?",
        "inputSchema": {
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
        "description": "Flag anomaly for review. Args: bill_id, reason, severity?",
        "inputSchema": {
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
        "description": "List session bills",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_tool(name: str, args: dict) -> dict:
    if name == "erp_create_bill":
        bill = Bill(
            id=f"BILL-{uuid4().hex[:8].upper()}",
            vendor_name=args["vendor_name"],
            invoice_number=args["invoice_number"],
            total=float(args["total"]),
            currency=args.get("currency", "USD"),
            status="pending_payment",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        BILLS[bill.id] = bill
        return asdict(bill)
    if name == "erp_flag_anomaly":
        row = {
            "id": f"ANOM-{uuid4().hex[:8].upper()}",
            "bill_id": args["bill_id"],
            "reason": args["reason"],
            "severity": args.get("severity", "medium"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        ANOMALIES.append(row)
        return row
    if name == "erp_list_bills":
        return {"bills": [asdict(b) for b in BILLS.values()]}
    raise ValueError(f"Unknown tool: {name}")


def respond(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if method == "initialize":
            respond(
                msg_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "clearance-erp", "version": "0.2.0"},
                },
            )
        elif method == "tools/list":
            respond(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                data = handle_tool(name, args)
                respond(
                    msg_id,
                    {
                        "content": [{"type": "text", "text": json.dumps(data)}],
                        "isError": False,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                respond(
                    msg_id,
                    {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                )
        elif method == "ping":
            respond(msg_id, {})
        else:
            respond(msg_id, error={"code": -32601, "message": f"Method not found: {method}"})


if __name__ == "__main__":
    main()
