# What I built (for hiring managers)

Project: **Clearance** · Author: **Sumith Shet** ([SumithShet18](https://github.com/SumithShet18))  
Live: https://clearance-1k8l.onrender.com · Repo: https://github.com/SumithShet18/clearance

---

## Summary

I designed, implemented, evaluated, and deployed a **multi-agent document operations system** that processes invoices and insurance-style claims through a governed pipeline: extraction, validation, policy, decisioning, human-in-the-loop, and ERP-style writeback — with audits, traces, and offline benchmarks.

---

## Scope of work (end-to-end ownership)

| Area | Delivered |
| --- | --- |
| Product design | AP + claims use cases, STP vs exception UX |
| Backend | FastAPI, async SQLAlchemy, case model, REST API |
| Agent system | Multi-step pipeline, task/progress ledgers, policy engine |
| Tools | MCP-shaped ERP tools + standalone stdio MCP server |
| Frontend | Operator UI: inbox, timeline, HITL, metrics, bench, export |
| Quality | Gold sets, synthetic generator, CORD fixtures, REPORT.md |
| Observability | Step timeline + JSONL spans per case |
| DevEx | Docker, Render blueprint, GitHub Actions CI, tests |
| Docs | Recruiter README, use cases, demo script, architecture |

---

## Skills demonstrated

- Agentic / multi-step LLM application design (not single-prompt apps)  
- Production concerns: HITL, irreversible actions, audit, evals  
- API and full-stack delivery  
- Evaluation harnesses and honest metrics  
- Cloud deploy (Docker + Render)  
- Clear technical writing for non-specialist readers  

---

## How to evaluate in 5 minutes

1. Open the live demo → seed  
2. Compare one auto-acted vs one HITL case  
3. Skim this file + [USE_CASES.md](USE_CASES.md)  
4. Optional: `evals/REPORT.md` for numbers  

---

## Honest limitations

- ERP is **mock** (integration-ready tool shape, not NetSuite production)  
- Default extractor is **mock/rules**; LLM/vision optional via API key  
- Free Render **cold starts**  
- Portfolio-grade multi-tenant security not in scope  

These are intentional scope choices for a shippable public demo.
