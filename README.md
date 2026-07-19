# Clearance

[![ci](https://github.com/SumithShet18/clearance/actions/workflows/ci.yml/badge.svg)](https://github.com/SumithShet18/clearance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

**Agents that finish work — measured, governed, and reversible.**

Portfolio project by [**SumithShet18**](https://github.com/SumithShet18)  
**Repo:** [github.com/SumithShet18/clearance](https://github.com/SumithShet18/clearance)

> Enterprise AI in 2026 fails on **quality, evals, and governance** — not model IQ.  
> Clearance is a production-shaped **multi-agent document operations** system that turns invoices into audited ERP actions with confidence gates, policy checks, human-in-the-loop, and offline gold evals.

---

## Demo (60 seconds)

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** → click **One-click demo seed** → open a case → export audit JSON.

### Docker

```bash
docker compose up --build
# http://localhost:8000
```

### What you will see

| Sample | Typical outcome |
| --- | --- |
| ACME / Northwind (clean) | **Auto-acted** → ERP bill + audit |
| High-value unknown vendor | **HITL** + anomaly flag → approve → bill |
| EUR / messy OCR | Escalate (currency / low confidence) |

Gold evals target **≥75% field accuracy** (clean set often ~100% in mock mode).

---

## Architecture

```
Browser UI
    │
    ▼
FastAPI ──► Agent pipeline (code-orchestrated graph)
              1 plan (task ledger)
              2 extract (mock | OpenAI)
              3 validate (schema + math)
              4 retrieve_policy
              5 decide
              6 flag_anomaly (on risk)
              7 HITL interrupt
              8 act → erp_create_bill (MCP-shaped)
              9 verify
    │
    ├── SQLite cases + audit
    ├── GET /api/evals/run  (offline gold set)
    ├── GET /api/cases/{id}/export  (compliance bundle)
    └── mcp-servers/erp  (stdio MCP tool server)
```

**Compose, don’t reinvent:**  
Agentgateway connects · HumanLayer schedules · JamJet polices · LangGraph runs graphs · **Clearance finishes the business case.**

See [docs/COMPETITIVE.md](docs/COMPETITIVE.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Why recruiters care

| Hiring signal | Evidence in this repo |
| --- | --- |
| Shipped production agents | Full case lifecycle + irreversible action gates |
| Evals & quality | `evals/gold` + CI + `/api/evals/run` |
| HITL / governance | Confidence + policy escalation queue |
| MCP / tools | Tool catalog + standalone ERP MCP server |
| System design | Magentic-One ledgers, Anthropic-style composition |
| Honesty | Competitive map — no “Vic.ai killer” claim |

**Resume bullet**

> Built Clearance, a multi-agent AP DocOps platform (HITL, policy checks, MCP-shaped ERP writeback, audit export, offline gold evals, Docker). Demo auto-resolves clean invoices and escalates high-risk cases with anomaly flags; CI enforces eval thresholds.

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Mode + version |
| POST | `/api/demo/seed` | Run all samples |
| GET | `/api/samples` | Sample list |
| POST | `/api/cases` | Upload |
| POST | `/api/cases/from-sample/{name}` | Run sample |
| GET | `/api/cases` | Inbox |
| GET | `/api/cases/{id}` | Timeline + extraction |
| POST | `/api/cases/{id}/review` | HITL approve/reject |
| GET | `/api/cases/{id}/export` | Audit JSON bundle |
| GET | `/api/cases/metrics/summary` | ROI metrics |
| GET | `/api/evals/run` | Gold field accuracy |
| GET | `/api/tools` | MCP tool descriptors |

Optional LLM: set `OPENAI_API_KEY` and `CLEARANCE_MODE=llm` (see `apps/api/.env.example`). Default is **mock** (offline, free, CI-stable).

---

## Clearance Bench (datasets + metrics)

Research-backed evaluation track (public invoice/receipt corpora + synthetic gold):

| Track | Source | Purpose |
| --- | --- | --- |
| **Synthetic** (default) | 50 reproducible invoices (no PII) | CI + portfolio numbers |
| **CORD v2** (optional) | HF `naver-clova-ix/cord-v2` | Real receipts credibility |
| **Manual** | `samples/invoice_*.txt` | Demo storytelling |

```bash
# from repo root
set PYTHONPATH=.
apps\api\.venv\Scripts\python evals\run_benchmark.py --source synthetic --limit 50 --pipeline
```

See published numbers in **[evals/REPORT.md](evals/REPORT.md)**.

API: `GET /api/evals/benchmark?source=synthetic&limit=50` · UI button **Run Clearance Bench (50)**.

## Tests

```bash
cd apps/api
pytest -q
```

CI: GitHub Actions on every push (unit + gold evals + API smoke).

---

## MCP ERP server

```bash
python mcp-servers/erp/server.py
# JSON-RPC over stdin: initialize | tools/list | tools/call
```

Tools: `erp_create_bill`, `erp_flag_anomaly`, `erp_list_bills` — same contracts as in-process tools.

---

## Repo layout

```
clearance/
  apps/api/          FastAPI + agent pipeline
  apps/web/          Operator UI
  samples/           Demo invoices
  evals/gold/        Labels + offline
  mcp-servers/erp/   Standalone MCP server
  docs/              Architecture + competitive map
  docker-compose.yml One-command deploy
```

---

## License

MIT © 2026 Sumith Shet

Built with production agent engineering patterns (Anthropic workflows, Magentic-One ledgers, MCP tool design) — not framework cosplay.
