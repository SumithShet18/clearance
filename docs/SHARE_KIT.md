# Share kit — what to do next (human checklist)

Live demo: **https://clearance-1k8l.onrender.com**  
Repo: **https://github.com/SumithShet18/clearance**  

Recruiter-facing docs: [USE_CASES.md](USE_CASES.md) · [DEMO.md](DEMO.md) · [WHAT_I_BUILT.md](WHAT_I_BUILT.md)

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
6. Point at metrics / Bench / [evals/REPORT.md](../evals/REPORT.md).  
7. **Export audit JSON** + observability spans.  
8. End with repo link.

Paste Loom into LinkedIn Featured. Reply with the URL to add it to README.

## 4. LinkedIn / X post (copy-paste)

```
Built Clearance — production multi-agent DocOps (not a chatbot).

Live: https://clearance-1k8l.onrender.com
Code: https://github.com/SumithShet18/clearance

• Multi-agent pipeline: plan → extract → validate → policy → decide → HITL → ERP act → verify
• Dual-track bench: synthetic (50) + CORD receipt fixtures (25)
• ~97.5% micro field accuracy on synthetic (with stress cases); pipeline ~52% STP / ~48% HITL
• MCP-shaped tools, audit export, JSONL traces

Compose agent infrastructure — finish the business case.
```

## 5. Resume bullet (copy-paste)

```
Built and deployed Clearance, a multi-agent document operations system (HITL, policy checks, MCP-shaped ERP writeback, gold evals, audit export). Live demo processes invoices/claims with measurable STP/HITL rates; dual-track bench on synthetic + CORD-derived fixtures. FastAPI, Docker, Render.
```

## 6. Roles to target

- AI / GenAI Application Engineer  
- Agentic systems / AI platform engineer  
- Full-stack engineer (AI products)  
- Forward-deployed / solutions engineer (enterprise AI)

Lead with Clearance in every application. Aim for **10+ applications this week**.

## 7. Interview arc (45 min)

1. Market: quality / pilot cancel risk  
2. Why not rebuild Agentgateway / control planes  
3. Agent graph + ledgers  
4. Evals + HITL design  
5. Live demo of clearance-1k8l.onrender.com  
