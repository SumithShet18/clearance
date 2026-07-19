# Clearance

[![ci](https://github.com/SumithShet18/clearance/actions/workflows/ci.yml/badge.svg)](https://github.com/SumithShet18/clearance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://clearance-1k8l.onrender.com)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

### Multi-agent document operations for back-office work  
**Invoices & claims in → policy checks → auto-post or human review → audited ERP action**

| | |
| --- | --- |
| **Live demo** | **[https://clearance-1k8l.onrender.com](https://clearance-1k8l.onrender.com)** |
| **Author** | [SumithShet18](https://github.com/SumithShet18) |
| **Cold start** | Free Render tier may take 30–60s on first open |

> **Not a chatbot.** Clearance is a production-shaped **agent system** that *finishes document work*, with human-in-the-loop only when risk is high.

---

## The problem (real world)

Finance and insurance teams drown in unstructured documents:

- Supplier **invoices** must be typed into an ERP (NetSuite, SAP, QuickBooks…)
- **Claims** (FNOL + repair estimates) must be triaged by adjusters
- Most “AI demos” answer questions — they don’t **write back** safely or leave an **audit trail**
- Enterprises care about **accuracy, straight-through processing (STP) %, and who approved what**

Clearance models that workflow end-to-end.

---

## What I built

A full-stack **multi-agent document ops product**:

| Layer | Capability |
| --- | --- |
| **Agent pipeline** | Plan → extract → validate → policy → decide → (HITL) → act → verify |
| **Governance** | Confidence thresholds, vendor/amount/currency policy, anomaly flags |
| **Human-in-the-loop** | Exception queue: approve / reject before irreversible ERP write |
| **Tools (MCP-shaped)** | `erp_create_bill`, `erp_flag_anomaly`, standalone MCP server |
| **Observability** | Per-step timeline + JSONL traces + audit export |
| **Evaluation** | Offline gold sets + dual-track bench (synthetic + CORD receipts) |
| **Ship** | Docker, CI, live HTTPS on Render |

**Resume line**

> Built and deployed Clearance, a multi-agent document operations system that processes invoices/claims with policy checks, human-in-the-loop escalation, MCP-shaped ERP writeback, audit export, and measured evals. Live demo + dual-track benchmark. FastAPI, Docker, Render.

---

## Use cases

### 1. Accounts payable (primary)

| | |
| --- | --- |
| **Who** | AP clerks, controllers, mid-market finance teams |
| **Input** | Supplier invoice (text/PDF/image path) |
| **Output** | Structured fields + **ERP bill** *or* exception for human |
| **Business value** | Lower touch rate on clean invoices; humans only on risk |

**In the demo**

| Sample | Outcome | Real-world meaning |
| --- | --- | --- |
| Clean known vendor (ACME) | `acted` + `BILL-…` | Straight-through processing |
| High $ / unknown vendor | `needs_review` | Exception queue |
| Non-USD / messy | Escalate | Policy / quality gate |

### 2. Insurance claims intake (second vertical)

| | |
| --- | --- |
| **Who** | Claims ops, carriers, TPAs |
| **Input** | First Notice of Loss + cost estimate |
| **Output** | Triage: auto-path vs senior adjuster |
| **Business value** | Speed on low severity; control on high severity |

Samples: `samples/claims/claim_auto_fnol.txt`, `claim_high_severity.txt`

### 3. Same pattern elsewhere (not all built — same architecture)

Procurement exceptions · vendor onboarding packs · lending document intake · any “document → decision → system of record” flow.

More detail: **[docs/USE_CASES.md](docs/USE_CASES.md)**

---

## 60-second demo (for recruiters)

1. Open **[live demo](https://clearance-1k8l.onrender.com)** (wait if cold-starting)  
2. Click **One-click demo seed**  
3. Open an **`acted`** case → agent timeline + ERP bill + audit  
4. Open a **`needs_review`** case → **Approve** → bill created after human  
5. Optional: **Export audit JSON** · **Observability spans** · **Run Clearance Bench**

Full walkthrough script: **[docs/DEMO.md](docs/DEMO.md)**

---

## How it works

```
Upload / sample document
        │
        ▼
┌─────────────────────────────────────────┐
│  Multi-agent pipeline                   │
│  plan → extract → validate → policy     │
│       → decide → HITL? → act → verify   │
└─────────────────────────────────────────┘
        │                    │
   low risk              high risk
        ▼                    ▼
  ERP create bill      Human review queue
  (auto STP)           then approve/reject
        │
        ▼
  Audit log + traces + metrics
```

| Concept | Implementation |
| --- | --- |
| Agent composition | Explicit graph (Anthropic-style workflows) |
| Task / progress state | Magentic-One–style ledgers |
| Tools | MCP-shaped ERP tools + `mcp-servers/erp` |
| Quality | Gold labels, per-field bench, CI |

Deep dive: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** · Competitive honesty: **[docs/COMPETITIVE.md](docs/COMPETITIVE.md)**

---

## Measured results

From **[evals/REPORT.md](evals/REPORT.md)**:

| Track | What | Result |
| --- | --- | --- |
| Synthetic (50) | Field accuracy (with stress cases) | **~97.5%** micro |
| Pipeline subset (25) | Auto-acted vs HITL | **~52% STP / ~48% HITL** |
| CORD v2 fixtures (25) | Public receipt labels (HF) | Track B in REPORT |

STP &lt; 100% is intentional: governance should *not* auto-post high-risk cases.

---

## Tech stack

| Area | Choice |
| --- | --- |
| API | Python, FastAPI, SQLAlchemy, SQLite |
| UI | Vanilla JS operator console (fast to demo) |
| Agents | Code-orchestrated multi-step graph + ledgers |
| Tools | In-process ERP mock + MCP stdio server |
| Eval | Custom gold sets + benchmark CLI |
| Deploy | Docker, Render free tier, GitHub Actions CI |

Optional: `CLEARANCE_MODE=llm` + `OPENAI_API_KEY` for LLM/vision extraction (default **mock** = free, offline, CI-stable).

---

## Repository structure

```
clearance/
├── README.md                 ← you are here (recruiter overview)
├── apps/
│   ├── api/                  ← FastAPI + agent pipeline + tests
│   └── web/                  ← operator UI (inbox, timeline, HITL)
├── samples/
│   ├── invoice_*.txt         ← AP demo cases
│   ├── claims/               ← insurance FNOL demo cases
│   ├── cord/                 ← CORD receipt text fixtures
│   └── synthetic/            ← 50-doc bench corpus
├── evals/
│   ├── REPORT.md             ← published benchmark numbers
│   ├── run_benchmark.py      ← Clearance Bench CLI
│   ├── gold/                 ← labels
│   └── datasets/             ← synthetic generator + CORD loader
├── mcp-servers/erp/          ← standalone MCP ERP tools
├── docs/
│   ├── USE_CASES.md          ← real-world use cases
│   ├── DEMO.md               ← how to demonstrate
│   ├── ARCHITECTURE.md       ← system design
│   ├── COMPETITIVE.md        ← what this is / isn’t
│   └── SHARE_KIT.md          ← LinkedIn / resume / pin checklist
├── Dockerfile · render.yaml  ← production deploy
└── scripts/                  ← local run / deploy notes
```

Technical inventory for hiring managers: **[docs/WHAT_I_BUILT.md](docs/WHAT_I_BUILT.md)**

---

## Quick start (local)

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000  

```bash
# tests
pytest -q

# benchmark
# from repo root, PYTHONPATH=. 
python evals/run_benchmark.py --source synthetic --limit 50 --pipeline
```

---

## API (summary)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| POST | `/api/demo/seed` | Batch demo cases |
| GET/POST | `/api/cases…` | Inbox, detail, HITL review, export, traces |
| GET | `/api/evals/benchmark` | Run field-accuracy bench |
| GET | `/api/tools` | MCP tool catalog |

---

## License

MIT © 2026 Sumith Shet

Built to demonstrate **production agent engineering**: multi-step work, tools, governance, evals — not framework cosplay.
