"""Integration tests for Clearance DocOps pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.erp import create_bill, flag_anomaly, list_anomalies, list_bills, reset_erp_state  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _clean():
    await init_db()
    reset_erp_state()
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield
    reset_erp_state()


@pytest.mark.asyncio
async def test_health_and_tools_catalog():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/api/health")
        assert h.status_code == 200
        body = h.json()
        assert body["product"] == "Clearance"
        assert body.get("version", "").startswith("0.")
        tools = await client.get("/api/tools")
        names = {t["name"] for t in tools.json()["tools"]}
        assert "erp_create_bill" in names
        assert "erp_flag_anomaly" in names


@pytest.mark.asyncio
async def test_sample_auto_resolves_and_creates_bill():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/cases/from-sample/invoice_acme_clean.txt")
        assert r.status_code == 200
        case_id = r.json()["id"]
        assert r.json()["status"] == "acted"
        d = await client.get(f"/api/cases/{case_id}")
        assert d.status_code == 200
        detail = d.json()
        assert detail["decision"] == "approve"
        assert detail["erp_bill_id"]
        assert len(detail["steps"]) >= 6
        assert detail["audit"]


@pytest.mark.asyncio
async def test_high_value_needs_review_then_approve():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/cases/from-sample/invoice_unknown_highvalue.txt")
        assert r.json()["status"] == "needs_review"
        case_id = r.json()["id"]
        d = await client.get(f"/api/cases/{case_id}")
        step_names = [s["name"] for s in d.json()["steps"]]
        assert "flag_anomaly" in step_names
        rev = await client.post(
            f"/api/cases/{case_id}/review",
            json={"action": "approve", "note": "ok"},
        )
        assert rev.status_code == 200
        assert rev.json()["status"] == "acted"
        assert rev.json()["erp_bill_id"]


@pytest.mark.asyncio
async def test_seed_demo_runs_multiple_samples():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/demo/seed")
        assert r.status_code == 200
        body = r.json()
        assert body["seeded"] >= 4
        cases = await client.get("/api/cases")
        assert len(cases.json()) >= 4
        m = await client.get("/api/cases/metrics/summary")
        assert m.json()["total_cases"] >= 4


@pytest.mark.asyncio
async def test_export_audit_bundle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/cases/from-sample/invoice_acme_clean.txt")
        case_id = r.json()["id"]
        exp = await client.get(f"/api/cases/{case_id}/export")
        assert exp.status_code == 200
        bundle = exp.json()
        assert bundle["case_id"] == case_id
        assert "audit" in bundle
        assert "extraction" in bundle
        assert "steps" in bundle


def test_flag_anomaly_tool():
    bill = create_bill("ACME Supplies", "INV-X", 100.0)
    anomaly = flag_anomaly(bill.id, reason="duplicate risk", severity="medium")
    assert anomaly["bill_id"] == bill.id
    assert anomaly["reason"] == "duplicate risk"
    assert list_anomalies()
    assert any(b.id == bill.id for b in list_bills())


@pytest.mark.asyncio
async def test_health_reports_erp_and_rate_limit():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/api/health")
        body = h.json()
        assert body["erp"] in {"mock", "mcp"}
        assert "rate_limit_per_minute" in body
        tools = await client.get("/api/tools")
        assert tools.json().get("backend") in {"mock", "mcp"}


def test_mcp_erp_backend_create_bill(monkeypatch):
    """CLEARANCE_ERP=mcp routes create_bill through mcp-servers/erp/server.py stdio."""
    from app.config import settings
    from app.services import erp as erp_mod

    monkeypatch.setattr(settings, "clearance_erp", "mcp")
    erp_mod.reset_erp_state()
    try:
        bill = create_bill("MCP Vendor", "INV-MCP-1", 42.5, "USD")
        assert bill.id.startswith("BILL-")
        assert bill.vendor_name == "MCP Vendor"
        assert bill.total == 42.5
    finally:
        monkeypatch.setattr(settings, "clearance_erp", "mock")
        erp_mod.reset_erp_state()


@pytest.mark.asyncio
async def test_rate_limit_trips_on_burst(monkeypatch):
    from app.config import settings
    from app.middleware_rate_limit import reset_rate_limit_state

    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    monkeypatch.setattr(settings, "require_demo_key", False)
    monkeypatch.setattr(settings, "demo_api_key", "")
    reset_rate_limit_state()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        codes = []
        for _ in range(5):
            r = await client.post("/api/cases/from-sample/invoice_acme_clean.txt")
            codes.append(r.status_code)
        assert 429 in codes
        assert codes.count(200) + codes.count(201) >= 1
    reset_rate_limit_state()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 30)
