# Architecture notes

## Graph (Phase 1)

Code-orchestrated pipeline in `app/services/pipeline.py`:

1. **ingest** — load document text  
2. **plan** — Task ledger (facts, guesses, plan, risk, effort)  
3. **extract** — mock regex/structure or OpenAI JSON  
4. **validate** — schema + arithmetic  
5. **retrieve_policy** — keyword policy retrieval (stand-in for agentic RAG)  
6. **decide** — approve / hold / escalate  
7. **hitl** — interrupt when confidence or policy requires human  
8. **act** — `erp_create_bill` (MCP-shaped tool)  
9. **verify** — confirm ERP id + decision  

## Why code-first orchestration

Anthropic and OpenAI both recommend mixing **deterministic code orchestration** with LLM judgment. Phase 1 maximizes demo reliability and testability; LangGraph adapters can wrap the same nodes without changing the HTTP product surface.

## Ledgers

Inspired by Microsoft Magentic-One:

- **Task ledger** — outer plan (what we’re doing)  
- **Progress ledger** — inner progress (where we are, stall, needs_human)

## Safety

- Auto path only when confidence ≥ threshold and policies pass  
- ERP writeback is treated as **irreversible** and logged in audit  
- Human approval required for low confidence, unknown high-value vendors, high totals, non-USD  

## Data

SQLite by default (`data/clearance.db`). Swap `DATABASE_URL` for Postgres when multi-user.
