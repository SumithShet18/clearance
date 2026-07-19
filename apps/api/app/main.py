from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import cases, evals
from app.services.erp import MCP_TOOLS


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Clearance",
    description=(
        "Production multi-agent document operations — extract, validate, policy-check, "
        "HITL, MCP-shaped ERP writeback, and evals. Compose, don't reinvent control planes."
    ),
    version="0.3.0",
    lifespan=lifespan,
)




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(evals.router)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mode": "llm" if settings.use_llm else "mock",
        "hitl_threshold": settings.confidence_hitl_threshold,
        "product": "Clearance",
        "version": "0.3.0",
        "skills": ["HITL", "MCP-tools", "gold-evals", "audit-export", "demo-seed", "clearance-bench"],
    }




@app.get("/api/tools")
async def tools():
    """MCP-shaped tool catalog (Phase 1: in-process mock ERP)."""
    return {"tools": MCP_TOOLS}


@app.get("/api/samples")
async def list_samples():
    root = Path(__file__).resolve().parents[3] / "samples"  # app->api->apps->clearance
    if not root.exists():
        return []
    return sorted(p.name for p in root.glob("*.txt"))


@app.post("/api/demo/seed")
async def seed_demo():
    """Run all sample invoices through the pipeline (portfolio one-click demo)."""
    from app.db import CaseRow, SessionLocal, new_id, now
    from app.models.schemas import CaseStatus
    from app.services.pipeline import run_pipeline

    root = Path(__file__).resolve().parents[3] / "samples"
    samples = sorted(root.glob("*.txt")) if root.exists() else []
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
