# Architecture

## High-level

```
┌──────────────┐     HTTPS      ┌──────────────────────────────────┐
│ Operator UI  │ ─────────────► │ FastAPI (apps/api)               │
│ (apps/web)   │                │  cases · review · evals · tools  │
└──────────────┘                └───────────────┬──────────────────┘
                                                │
                                ┌───────────────▼──────────────────┐
                                │ Agent pipeline                   │
                                │ plan → extract → validate →      │
                                │ policy → decide → HITL? →        │
                                │ act (ERP tool) → verify          │
                                └───────────────┬──────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────┐
                    ▼                           ▼                   ▼
              SQLite cases                 JSONL traces        MCP ERP server
              + audit JSON                 (data/traces)       (optional stdio)
```

## Pipeline stages

| Stage | Role |
| --- | --- |
| **ingest** | Load document text / image-derived text |
| **plan** | Task ledger (facts, plan, risk, effort) |
| **extract** | Structured fields (mock or LLM/vision) |
| **validate** | Schema + math integrity |
| **retrieve_policy** | Policy snippets (vendor, value, currency…) |
| **decide** | approve / hold / escalate |
| **flag_anomaly** | On risk — MCP-shaped tool |
| **hitl** | Interrupt until human approve/reject |
| **act** | `erp_create_bill` (irreversible gate) |
| **verify** | Final state check |

## Design principles

1. **Orchestration is software** — explicit graph, not prompt soup  
2. **HITL is selective** — only low confidence or policy risk  
3. **Irreversible actions are gated** — no silent ERP writes on risk  
4. **Measure quality** — gold labels + bench CLI  
5. **Compose infrastructure** — don’t rebuild gateways/control planes  

See [COMPETITIVE.md](COMPETITIVE.md) for ecosystem positioning.

## Key modules

| Path | Responsibility |
| --- | --- |
| `apps/api/app/services/pipeline.py` | Agent graph |
| `apps/api/app/services/extractor.py` | Mock / LLM / vision extract |
| `apps/api/app/services/policy.py` | Business rules |
| `apps/api/app/services/erp.py` | ERP tools |
| `apps/api/app/services/traces.py` | JSONL spans |
| `apps/api/app/routers/cases.py` | Case API + HITL + export |
| `evals/run_benchmark.py` | Clearance Bench |
| `mcp-servers/erp/server.py` | Standalone MCP tools |

## Data

- Cases: SQLite (`data/clearance.db` local; ephemeral on free Render)  
- Uploads: `data/uploads/`  
- Traces: `data/traces/{case_id}.jsonl`  
