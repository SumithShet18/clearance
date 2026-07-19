# Clearance

**Agents that finish work — measured, governed, and reversible.**

Clearance is a production-shaped **multi-agent document operations** system for AP invoices (v1): extract → validate → policy check → decide → human-in-the-loop → MCP-shaped ERP writeback → verify — with **offline gold evals** and full audit trails.

> This is **not** another agent control plane.  
> Infrastructure (gateways, schedulers, policy engines) already exists open source.  
> Clearance **composes** those patterns into a business system that ships outcomes.

## Why this exists

| Market fact (2026) | Clearance response |
| --- | --- |
| Quality is the #1 agent production barrier | Gold eval suite + confidence gates |
| Evals lag observability | `/api/evals/run` offline harness Day 1 |
| Multi-agent projects get canceled | HITL, audit, irreversible-action gates |
| Control plane OSS is crowded | Compose, don’t clone (see `docs/COMPETITIVE.md`) |
| AP automation vendors are mature | Showcase vertical, not “Vic.ai killer” |

## Quick start

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000**

- Click a **sample** (clean invoices often auto-resolve)
- Messy / high-value / unknown-vendor / EUR samples hit **HITL**
- **Run gold evals** for field accuracy metrics

### Optional LLM mode

```bash
copy .env.example .env
# set OPENAI_API_KEY=... and CLEARANCE_MODE=llm
```

Default is **mock mode** (deterministic, offline, free) — required for reliable demos and CI.

## Architecture

```
Browser UI  →  FastAPI  →  Agent pipeline (code-orchestrated graph)
                              ├─ plan (task ledger)
                              ├─ extract (mock | OpenAI)
                              ├─ validate (schema + math)
                              ├─ retrieve_policy
                              ├─ decide
                              ├─ hitl (interrupt)
                              ├─ act (erp_create_bill)
                              └─ verify
                         Postgres/SQLite · audit · evals
```

Patterns drawn from Anthropic (workflow composition), Magentic-One (task/progress ledgers), and MCP tool design (ERP tools as documented tool surfaces).

## Repo layout

```
clearance/
  apps/api/          # FastAPI backend + pipeline
  apps/web/          # Operator UI
  samples/           # Demo invoices (text)
  evals/gold/        # Gold labels for offline eval
  mcp-servers/erp/   # MCP server sketch for ERP tools
  docs/              # Competitive map, architecture notes
```

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Mode + version |
| GET | `/api/samples` | Demo files |
| POST | `/api/cases` | Upload invoice |
| POST | `/api/cases/from-sample/{name}` | Run sample |
| GET | `/api/cases` | List |
| GET | `/api/cases/{id}` | Timeline + extraction |
| POST | `/api/cases/{id}/review` | HITL approve/reject |
| GET | `/api/cases/metrics/summary` | ROI-style metrics |
| GET | `/api/evals/run` | Gold field accuracy |
| GET | `/api/tools` | MCP-shaped tool catalog |

## Evals (CI-friendly)

```bash
cd apps/api
pytest ../../evals/test_gold.py -q
# or hit GET /api/evals/run
```

## Resume bullet (fill after you measure)

> Built Clearance, a multi-agent AP DocOps system with HITL, policy checks, MCP-shaped ERP writeback, audit logs, and offline gold evals; demo auto-resolves clean invoices and escalates low-confidence / policy-risk cases.

## License

MIT — use it, fork it, put it in your portfolio. Don’t pretend you invented agent gateways.

## Roadmap

- [x] Phase 1 vertical slice (pipeline + UI + evals + HITL)
- [ ] LangGraph node adapters (same product API)
- [ ] Langfuse / OTEL export
- [ ] Real MCP server process for ERP
- [ ] Claims multi-doc pack (v2 vertical)
- [ ] Online eval sampling
