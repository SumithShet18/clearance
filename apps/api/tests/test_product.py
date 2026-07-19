"""Product-path tests: PDF intake, edit_and_approve, bills CSV, settings, auth."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))
sys.path.insert(0, str(ROOT))

from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.erp import reset_erp_state  # noqa: E402
from app.middleware_rate_limit import reset_rate_limit_state  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _clean():
    await init_db()
    reset_erp_state()
    reset_rate_limit_state()
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield
    reset_erp_state()
    reset_rate_limit_state()


@pytest.mark.asyncio
async def test_upload_txt_and_auto_or_review():
    transport = ASGITransport(app=app)
    sample = ROOT / "samples" / "invoice_acme_clean.txt"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with sample.open("rb") as f:
            r = await client.post(
                "/api/cases",
                files={"file": ("invoice_acme_clean.txt", f, "text/plain")},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in {"acted", "needs_review"}
        d = await client.get(f"/api/cases/{body['id']}")
        assert d.status_code == 200
        if body["status"] == "acted":
            assert d.json()["erp_bill_id"]
            bills = await client.get("/api/bills")
            assert any(b["id"] == d.json()["erp_bill_id"] for b in bills.json())


@pytest.mark.asyncio
async def test_edit_and_approve_posts_bill():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/cases/from-sample/invoice_unknown_highvalue.txt")
        assert r.json()["status"] == "needs_review"
        case_id = r.json()["id"]
        rev = await client.post(
            f"/api/cases/{case_id}/review",
            json={
                "action": "edit_and_approve",
                "note": "fixed fields",
                "extraction": {
                    "vendor_name": "ACME Supplies",
                    "invoice_number": "INV-EDIT-1",
                    "invoice_date": "2024-01-15",
                    "currency": "USD",
                    "subtotal": 100.0,
                    "tax": 0.0,
                    "total": 100.0,
                    "vendor_confidence": 1.0,
                    "invoice_number_confidence": 1.0,
                    "invoice_date_confidence": 1.0,
                    "total_confidence": 1.0,
                    "line_items": [],
                },
            },
        )
        assert rev.status_code == 200
        assert rev.json()["status"] == "acted"
        assert rev.json()["erp_bill_id"]
        bills = await client.get("/api/bills")
        assert any(b["invoice_number"] == "INV-EDIT-1" for b in bills.json())
        csv_r = await client.get("/api/bills/export.csv")
        assert csv_r.status_code == 200
        assert "INV-EDIT-1" in csv_r.text


@pytest.mark.asyncio
async def test_settings_and_case_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s = await client.get("/api/settings")
        assert s.status_code == 200
        put = await client.put(
            "/api/settings",
            json={
                "company_name": "Test Co",
                "known_vendors": ["ACME Supplies", "Northwind Traders"],
                "high_value_threshold": 5000,
                "unknown_vendor_threshold": 100,
                "confidence_hitl_threshold": 0.8,
                "allowed_currencies": ["USD", "EUR"],
            },
        )
        assert put.status_code == 200
        assert put.json()["company_name"] == "Test Co"
        await client.post("/api/cases/from-sample/invoice_acme_clean.txt")
        await client.post("/api/cases/from-sample/invoice_unknown_highvalue.txt")
        needs = await client.get("/api/cases?status=needs_review")
        assert needs.status_code == 200
        assert all(c["status"] == "needs_review" for c in needs.json())


@pytest.mark.asyncio
async def test_pdf_ingest_module():
    from app.services.ingest import extract_text_from_pdf, load_upload
    import tempfile

    # minimal valid-ish PDF bytes may fail gracefully
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
        path = Path(f.name)
    text, meta = extract_text_from_pdf(path)
    assert isinstance(text, str)
    assert meta.get("mode") in {"pdf_text", "pdf_empty", "pdf_error", "pdf_missing_dep"}
    path.unlink(missing_ok=True)

    raw = b"Vendor: ACME Supplies\nInvoice Number: INV-1\nTotal: 10.00\n"
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(raw)
        tpath = Path(f.name)
    text2, meta2, is_img = load_upload(tpath, "inv.txt", raw)
    assert not is_img
    assert "ACME" in text2
    tpath.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_auth_login_when_password_set(monkeypatch):
    from app.config import settings
    from app.workspace_auth import set_db_password_hash

    set_db_password_hash("")
    monkeypatch.setattr(settings, "clearance_password", "secret-test")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/api/cases")
        assert denied.status_code == 401
        bad = await client.post("/api/auth/login", json={"password": "wrong"})
        assert bad.status_code == 401
        ok = await client.post("/api/auth/login", json={"password": "secret-test"})
        assert ok.status_code == 200
        assert ok.json()["ok"] is True
        allowed = await client.get("/api/cases")
        assert allowed.status_code == 200
    monkeypatch.setattr(settings, "clearance_password", "")
    set_db_password_hash("")


@pytest.mark.asyncio
async def test_ui_setup_password_without_env():
    """Workspace password via API (no CLEARANCE_PASSWORD) — Render-safe path."""
    from app.config import settings
    from app.workspace_auth import set_db_password_hash, auth_enabled

    monkeypatch_pw = ""
    # ensure open
    object.__setattr__(settings, "clearance_password", "")
    set_db_password_hash("")
    assert not auth_enabled()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        open_cases = await client.get("/api/cases")
        assert open_cases.status_code == 200
        setup = await client.post("/api/auth/setup", json={"password": "ui-pass-99"})
        assert setup.status_code == 200
        assert setup.json()["ok"] is True
        assert auth_enabled()
        # new client without cookie should be denied
        async with AsyncClient(transport=transport, base_url="http://test") as client2:
            denied = await client2.get("/api/cases")
            assert denied.status_code == 401
            login = await client2.post("/api/auth/login", json={"password": "ui-pass-99"})
            assert login.status_code == 200
            ok = await client2.get("/api/cases")
            assert ok.status_code == 200
    set_db_password_hash("")
