# How to demonstrate Clearance

**Live:** https://clearance-1k8l.onrender.com  

If the page is slow: free Render cold start — wait 30–60s, refresh once.

---

## 5-minute script

### 1. Hook (15s)
> “This isn’t a chatbot. It’s a multi-agent system that processes business documents, applies policy, and either auto-posts to an ERP-style system or escalates to a human — with a full audit trail.”

### 2. Seed (30s)
- Click **One-click demo seed**  
- Show metrics: cases, auto-resolved, needs review  

### 3. Happy path (60s)
- Open an **`acted`** case (e.g. ACME / Northwind)  
- Show agent timeline steps  
- Point to **ERP bill id** and audit log  

> “Clean invoice, known vendor → straight-through processing.”

### 4. Risk path — key moment (90s)
- Open **`needs_review`** (high value, EUR, or high-severity claim)  
- Show policy / confidence / HITL panel  
- Click **Approve → create ERP bill**  
- Show status becomes **acted** and audit records human approval  

> “Production systems must not auto-pay risk. Humans stay in the loop.”

### 5. Proof (45s)
- **Export audit JSON**, or  
- **Observability spans**, or  
- **Bench honesty:** [evals/REPORT.md](../evals/REPORT.md) — synthetic ~97.5%; SROIE **assisted** ~98% vs **hard OCR-only** ~79.5%; pipeline ~52% STP / ~48% HITL  

> “We publish the hard track on purpose — high scores without a caveat are a red flag.”

### 6. Close (15s)
> “Code is open source; demo is live. Stack is what AI application teams hire for: agents, tools, evals, governance.”

---

## 90-second version

Seed → one `acted` → one `needs_review` + approve → “repo + live URL.”

---

## What each status means

| Status | Meaning |
| --- | --- |
| `acted` | Agents completed writeback (STP) |
| `needs_review` | Waiting on human (exception queue) |
| `rejected` | Human rejected — no bill |
