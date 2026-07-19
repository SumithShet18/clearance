# Share kit — what to do next (human checklist)

Live demo: **https://clearance-1k8l.onrender.com** (v0.5.0)  
Repo: **https://github.com/SumithShet18/clearance**  

Recruiter-facing docs: [USE_CASES.md](USE_CASES.md) · [DEMO.md](DEMO.md) · [WHAT_I_BUILT.md](WHAT_I_BUILT.md) · [evals/REPORT.md](../evals/REPORT.md)

**Product is portfolio-complete.** This week’s ROI is pin · Loom · LinkedIn · applications — not more features.

---

## 1. Pin on GitHub (2 min)

1. Open https://github.com/SumithShet18  
2. **Customize your pins**  
3. Pin **clearance**

## 2. Cold-start note (for demos)

Render free tier sleeps after idle. First open can take **30–60 seconds**.  
If the page is slow: wait, refresh once, then use **One-click demo seed**.

Optional: free [UptimeRobot](https://uptimerobot.com) HTTP(s) monitor every 5 min →  
`https://clearance-1k8l.onrender.com/api/health`  
(reduces cold starts during active job search)

## 3. Loom script (3–5 min)

Record on the **live** site:

1. “Most AI agents die in pilot. Clearance finishes document work with evals and human-in-the-loop.”  
2. Open live URL (mention cold start if needed).  
3. **One-click demo seed** → show inbox.  
4. ACME / Northwind → **acted** + ERP bill id.  
5. High-value or claim → **needs_review** → Approve → audit.  
6. Point at [evals/REPORT.md](../evals/REPORT.md): synthetic ~97.5%; **SROIE hard (OCR-only) ~79.5%** vs assisted ~98% (honest about label assist).  
7. **Export audit JSON** + observability spans.  
8. End with repo link.

Paste Loom into LinkedIn Featured. Reply with the URL to add it to README.

## 4. LinkedIn / X post (copy-paste)

```
Built Clearance — production multi-agent DocOps (not a chatbot).

Live: https://clearance-1k8l.onrender.com
Code: https://github.com/SumithShet18/clearance

• Pipeline: plan → extract → validate → policy → decide → HITL → ERP act → verify
• Multi-track bench: synthetic ~97.5% · ICDAR SROIE hard (OCR-only) ~79.5% · assisted ~98% (format-helped) · CORD fixtures
• Pipeline governance ~52% STP / ~48% HITL (by design)
• MCP ERP tools (mock or stdio process), audit export, JSONL traces, public rate limit

Compose agent infrastructure — finish the business case.
```

## 5. Resume bullet (copy-paste)

```
Built and deployed Clearance, a multi-agent document operations system with policy checks, human-in-the-loop escalation, MCP ERP writeback (in-process or stdio), gold evals, and audit export. Live demo; multi-track bench including honest OCR-hard SROIE (~79.5% micro) vs format-assisted labels, plus ~52% STP / ~48% HITL. FastAPI, Docker, Render.
```

## 6. Interview one-liner (evals honesty)

> “Assisted SROIE hits ~98% partly because of labeled Vendor/Total lines. Hard OCR-only drops to ~79.5% — that’s why policy and HITL exist, not just OCR accuracy. Miss gallery is in the repo.”

Point at: [evals/results/failures.md](../evals/results/failures.md)

## 7. Roles to target

- AI / GenAI Application Engineer  
- Agentic systems / AI platform engineer  
- Full-stack engineer (AI products)  
- Forward-deployed / solutions engineer (enterprise AI)

Lead with Clearance in every application. Aim for **10+ applications this week**.

## 8. Interview arc (45 min)

1. Market: quality / pilot cancel risk  
2. Why not rebuild Agentgateway / control planes  
3. Agent graph + ledgers  
4. Evals honesty (assisted vs hard SROIE) + HITL design  
5. Live demo of clearance-1k8l.onrender.com  
6. Optional: MCP mode / rate limit as production-shaped demo hardening  

---

## Optional later (only if a JD demands it)

- Vision bench row with `OPENAI_API_KEY`  
- Langfuse / OTEL export of JSONL spans  
- Stricter `DEMO_API_KEY` gate on Render  

Default: **stop building — apply.**
