"""ERP writeback — in-process mock or MCP stdio process (CLEARANCE_ERP=mcp)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings


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

_MCP_LOCK = threading.Lock()
_MCP_PROC: subprocess.Popen[str] | None = None
_MCP_MSG_ID = 0


def _mcp_server_path() -> Path:
    # apps/api/app/services/erp.py → repo root
    return Path(__file__).resolve().parents[4] / "mcp-servers" / "erp" / "server.py"


def _mcp_rpc(method: str, params: dict | None = None) -> dict:
    """JSON-RPC over stdin/stdout to mcp-servers/erp/server.py."""
    global _MCP_PROC, _MCP_MSG_ID
    server = _mcp_server_path()
    if not server.exists():
        raise RuntimeError(f"MCP ERP server not found at {server}")

    with _MCP_LOCK:
        if _MCP_PROC is None or _MCP_PROC.poll() is not None:
            _MCP_PROC = subprocess.Popen(
                [sys.executable, str(server)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            # handshake
            _MCP_MSG_ID += 1
            init = {
                "jsonrpc": "2.0",
                "id": _MCP_MSG_ID,
                "method": "initialize",
                "params": {},
            }
            assert _MCP_PROC.stdin and _MCP_PROC.stdout
            _MCP_PROC.stdin.write(json.dumps(init) + "\n")
            _MCP_PROC.stdin.flush()
            _MCP_PROC.stdout.readline()

        _MCP_MSG_ID += 1
        req = {
            "jsonrpc": "2.0",
            "id": _MCP_MSG_ID,
            "method": method,
            "params": params or {},
        }
        assert _MCP_PROC.stdin and _MCP_PROC.stdout
        _MCP_PROC.stdin.write(json.dumps(req) + "\n")
        _MCP_PROC.stdin.flush()
        line = _MCP_PROC.stdout.readline()
        if not line:
            err = (_MCP_PROC.stderr.read() if _MCP_PROC.stderr else "") or "no response"
            raise RuntimeError(f"MCP ERP empty response: {err}")
        return json.loads(line)


def _mcp_tool(name: str, arguments: dict) -> dict:
    resp = _mcp_rpc("tools/call", {"name": name, "arguments": arguments})
    if "error" in resp:
        raise RuntimeError(str(resp["error"]))
    result = resp.get("result") or {}
    if result.get("isError"):
        content = result.get("content") or []
        msg = content[0].get("text") if content else "MCP tool error"
        raise RuntimeError(str(msg))
    content = result.get("content") or []
    text = content[0].get("text") if content else "{}"
    data = json.loads(text) if isinstance(text, str) else text
    return data if isinstance(data, dict) else {"result": data}


def _bill_from_dict(d: dict) -> Bill:
    return Bill(
        id=str(d["id"]),
        vendor_name=str(d["vendor_name"]),
        invoice_number=str(d["invoice_number"]),
        total=float(d["total"]),
        currency=str(d.get("currency") or "USD"),
        status=str(d.get("status") or "pending_payment"),
        created_at=str(d.get("created_at") or datetime.now(timezone.utc).isoformat()),
    )


def create_bill(
    vendor_name: str,
    invoice_number: str,
    total: float,
    currency: str = "USD",
) -> Bill:
    if settings.erp_backend == "mcp":
        data = _mcp_tool(
            "erp_create_bill",
            {
                "vendor_name": vendor_name,
                "invoice_number": invoice_number,
                "total": total,
                "currency": currency,
            },
        )
        bill = _bill_from_dict(data)
        _BILLS[bill.id] = bill  # mirror for list_bills/audit in-process
        return bill

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
    if settings.erp_backend == "mcp":
        data = _mcp_tool(
            "erp_flag_anomaly",
            {"bill_id": bill_id, "reason": reason, "severity": severity},
        )
        anomaly = Anomaly(
            id=str(data["id"]),
            bill_id=str(data["bill_id"]),
            reason=str(data["reason"]),
            severity=str(data.get("severity") or severity),
            created_at=str(data.get("created_at") or datetime.now(timezone.utc).isoformat()),
        )
        _ANOMALIES[anomaly.id] = anomaly
        return asdict(anomaly)

    if bill_id not in _BILLS and not bill_id.startswith("BILL-"):
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
    if settings.erp_backend == "mcp":
        try:
            data = _mcp_tool("erp_list_bills", {})
            bills = data.get("bills") or []
            out = [_bill_from_dict(b) for b in bills]
            _BILLS.clear()
            for b in out:
                _BILLS[b.id] = b
            return out
        except Exception:  # noqa: BLE001 — fall back to mirror
            return list(_BILLS.values())
    return list(_BILLS.values())


def list_anomalies() -> list[Anomaly]:
    return list(_ANOMALIES.values())


def get_bill(bill_id: str) -> Bill | None:
    return _BILLS.get(bill_id)


def reset_erp_state() -> None:
    """Test helper — clears in-process state and MCP subprocess."""
    global _MCP_PROC
    _BILLS.clear()
    _ANOMALIES.clear()
    with _MCP_LOCK:
        if _MCP_PROC is not None and _MCP_PROC.poll() is None:
            try:
                _MCP_PROC.terminate()
                _MCP_PROC.wait(timeout=2)
            except Exception:  # noqa: BLE001
                try:
                    _MCP_PROC.kill()
                except Exception:  # noqa: BLE001
                    pass
        _MCP_PROC = None


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
