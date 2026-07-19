from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import AuthMiddleware
from app.config import settings
from app.db import init_db
from app.middleware_rate_limit import RateLimitMiddleware
from app.routers import auth_api, bills, cases, evals, settings_api
from app.services.erp import MCP_TOOLS

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Clearance",
    description=(
        "Single-tenant AP document operations — upload invoices, policy checks, "
        "HITL review, ERP bills, CSV export. Compose agents that finish work."
    ),
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(auth_api.router)
app.include_router(cases.router)
app.include_router(bills.router)
app.include_router(settings_api.router)
app.include_router(evals.router)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mode": "llm" if settings.use_llm else "mock",
        "erp": settings.erp_backend,
        "auth_required": settings.auth_required,
        "demo_mode": settings.clearance_demo,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "hitl_threshold": settings.confidence_hitl_threshold,
        "product": "Clearance",
        "version": VERSION,
        "skills": [
            "HITL",
            "edit-and-approve",
            "PDF-intake",
            "image-upload",
            "MCP-tools",
            "durable-bills",
            "csv-export",
            "settings",
            "duplicate-guard",
            "session-auth",
            "gold-evals",
            "clearance-bench",
        ],
    }


@app.get("/api/tools")
async def tools():
    return {"tools": MCP_TOOLS, "backend": settings.erp_backend}


@app.get("/api/samples")
async def list_samples():
    if not settings.clearance_demo:
        return []
    root = Path(__file__).resolve().parents[3] / "samples"
    if not root.exists():
        return []
    out: list[str] = []
    for p in sorted(root.rglob("*.txt")):
        rel = p.relative_to(root).as_posix()
        if rel.startswith("synthetic/") or rel.startswith("sroie_hard/"):
            continue
        if rel.startswith("sroie/") and not rel.endswith(("000.txt", "001.txt", "002.txt")):
            continue
        out.append(rel)
    return out


@app.post("/api/demo/seed")
async def seed_demo():
    if not settings.clearance_demo:
        raise HTTPException(403, "Demo mode disabled (CLEARANCE_DEMO=false)")
    from app.db import CaseRow, SessionLocal, new_id, now
    from app.models.schemas import CaseStatus
    from app.services.pipeline import run_pipeline

    root = Path(__file__).resolve().parents[3] / "samples"
    samples = []
    if root.exists():
        samples.extend(sorted(root.glob("*.txt")))
        claims = root / "claims"
        if claims.exists():
            samples.extend(sorted(claims.glob("*.txt")))
    created: list[dict] = []
    async with SessionLocal() as session:
        for path in samples:
            text = path.read_text(encoding="utf-8")
            case_id = new_id()
            row = CaseRow(
                id=case_id,
                filename=path.name,
                status=CaseStatus.pending.value,
                content_text=text,
                file_path=str(path),
                created_at=now(),
                updated_at=now(),
                archived=0,
            )
            session.add(row)
            await session.commit()
            await run_pipeline(session, row)
            await session.refresh(row)
            created.append({"id": row.id, "filename": row.filename, "status": row.status})
    return {"seeded": len(created), "cases": created}


@app.get("/")
async def index():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Clearance API", "docs": "/docs"}


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
