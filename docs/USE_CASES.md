# Real-world use cases

Clearance targets **document-heavy back-office work**: systems that must extract data, apply policy, optionally involve a human, then write to a system of record.

---

## 1. Accounts payable (AP) automation — primary

### Who uses it
- AP clerks and finance ops  
- Controllers who care about audit and exception rates  
- Mid-market companies with many supplier invoices  

### Today’s manual process
1. Invoice arrives (email PDF / portal)  
2. Human reads vendor, amount, line items  
3. Human enters data into ERP  
4. Approvals for high amounts / new vendors  
5. Weak trail of *why* something was paid  

### What Clearance does
| Step | Product behavior |
| --- | --- |
| Capture | Upload or sample invoice |
| Extract | Vendor, invoice #, dates, totals, lines |
| Validate | Schema + arithmetic checks |
| Policy | Unknown vendor, high value, non-USD, low confidence |
| Decide | Auto-approve vs hold |
| Act | Create ERP bill (MCP-shaped tool) **only** when allowed |
| Prove | Audit log + export JSON |

### Business outcomes
- Higher **straight-through processing** on clean invoices  
- Humans spend time on **exceptions**, not typing  
- **Auditability** for month-end and compliance  

### Demo mapping
| Live sample | Meaning |
| --- | --- |
| `invoice_acme_clean.txt` | Happy path STP |
| `invoice_unknown_highvalue.txt` | Risk → HITL |
| `invoice_eur_currency.txt` | Policy hold |
| `invoice_messy_lowconf.txt` | Quality gate |

---

## 2. Insurance claims intake (FNOL) — secondary vertical

### Who uses it
- Claims handlers / adjusters  
- Carriers and third-party administrators  

### Today’s manual process
1. First Notice of Loss + repair estimate  
2. Human triages severity  
3. Low complexity may fast-track; high complexity escalates  
4. Documentation must support later review  

### What Clearance does
Same agent graph; claim-flavored samples:

| Sample | Outcome intent |
| --- | --- |
| `claims/claim_auto_fnol.txt` | Lower amount, known-style path → can auto-act |
| `claims/claim_high_severity.txt` | High $ / unknown vendor → HITL |

Real deployments would connect to a claims system instead of mock ERP and keep humans on **payout authority**.

---

## 3. Adjacent use cases (same product pattern)

Not all implemented as separate UIs — architecture applies:

| Domain | Documents | Auto vs human |
| --- | --- | --- |
| Procurement | PO mismatch, vendor packs | Mismatch → buyer |
| Lending / KYC ops | Bank docs, applications | Fraud flag → analyst |
| Healthcare ops | Admin packets (non-clinical) | Policy → specialist |
| Contract ops | Standard clauses | Unusual clause → counsel |

---

## What a real customer deployment would add

Clearance already shows the **agent + governance core**. Production SaaS would add:

- SSO, multi-tenant isolation  
- Real ERP / claims connectors (NetSuite, Guidewire, etc.)  
- Email/S3 ingest  
- SLAs, PII controls, SOC2  

That gap is expected for a portfolio product — and easy to discuss in interviews.

---

## One-sentence pitch by audience

| Audience | Pitch |
| --- | --- |
| **Recruiter** | “I shipped a live multi-agent system that processes invoices and claims with HITL and audits.” |
| **Engineering manager** | “Production agent graph, tools, evals, traces — not a notebook demo.” |
| **Ops / domain** | “Exception-first automation: agents do the typing; people decide risk.” |
