# Clearance User Guide — single-tenant AP product

Clearance is a **document operations workspace** for accounts payable: upload invoices, review exceptions, post bills, export CSV for your accountant.

**Live public demo:** https://clearance-1k8l.onrender.com (open access; may sleep on free tier)  
**Recommended for real use:** self-host with Docker + password + data volume.

---

## 10-minute self-host

```bash
git clone https://github.com/SumithShet18/clearance.git
cd clearance
```

### Option A — Docker Compose (recommended)

```bash
# set a workspace password
export CLEARANCE_PASSWORD=choose-a-strong-password
export CLEARANCE_DEMO=false   # hide portfolio seed/bench

docker compose up --build -d
```

Open http://localhost:8000 → sign in with your password.

Data lives in the `clearance-data` volume (`/app/data` inside the container): SQLite DB + uploads.

### Option B — Local Python

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# Windows PowerShell
$env:CLEARANCE_PASSWORD="your-password"
$env:CLEARANCE_DEMO="false"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Login / logout — when it appears

Login **only shows if the server has a password**:

| `CLEARANCE_PASSWORD` | What you see |
| --- | --- |
| **empty** (default) | **No login, no logout** — open access. Badge shows `open access`. |
| **set** (e.g. `mysecret`) | Login card on open; **Log out** after sign-in |

Check: open `/api/auth/status` — if `"auth_required": false`, password is not set.

### Enable login on Render

1. [Render Dashboard](https://dashboard.render.com) → your **clearance** service  
2. **Environment** → **Add Environment Variable**  
3. Key: `CLEARANCE_PASSWORD` · Value: your password  
4. **Save** → service restarts  
5. Hard-refresh the site (Ctrl+Shift+R)  
6. You should see the sign-in card; after login, **Log out** in the top bar  

### Enable login locally

```powershell
$env:CLEARANCE_PASSWORD="mysecret"
uvicorn app.main:app --port 8000
```

Then open http://127.0.0.1:8000

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `CLEARANCE_PASSWORD` | empty | If set, login required for all API writes/reads (except health/auth) |
| `CLEARANCE_DEMO` | `true` | Show demo seed / samples / evals |
| `CLEARANCE_MODE` | `mock` | `mock` rules or `llm` + OpenAI |
| `OPENAI_API_KEY` | — | Vision / LLM extraction |
| `CLEARANCE_ERP` | `mock` | `mcp` for stdio MCP ERP process |
| `SESSION_SECRET` | dev default | **Change in production** |
| `RATE_LIMIT_PER_MINUTE` | `60` | Mutating request limit per IP |

---

## Daily workflow

1. **Upload** PDF (text layer), image, or `.txt` invoice.  
2. Clean known vendors may **auto-post** → bill appears under **Bills**.  
3. Risky cases land in **Needs review** — edit vendor / amount / invoice # → **Save & post bill**.  
4. **Download bills CSV** for accounting import.  
5. **Settings** — maintain known vendors, high-value threshold, confidence bar.

### PDF notes

- Digital PDFs with a text layer extract offline (no API key).  
- Scanned PDFs (image-only) need manual entry in review **or** `CLEARANCE_MODE=llm` + `OPENAI_API_KEY` for vision.

### Duplicate guard

Same vendor + invoice number already posted → policy hold (POL-004). No silent double-post.

---

## Backup

Copy the data directory / volume:

- Docker volume `clearance-data`  
- Or `data/clearance.db` + `data/uploads/` when running locally  

---

## API (authenticated when password set)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | `{ "password": "…" }` → session cookie |
| POST | `/api/cases` | Multipart upload |
| GET | `/api/cases?status=needs_review` | Inbox filter |
| POST | `/api/cases/{id}/review` | approve / reject / edit_and_approve |
| GET | `/api/bills` | Posted bills |
| GET | `/api/bills/export.csv` | Accountant export |
| GET/PUT | `/api/settings` | Policy workspace settings |

---

## Security notes

- Single shared password is for **one company / trusted network**, not multi-tenant SaaS.  
- Use HTTPS (reverse proxy or hosted TLS) in production.  
- Set a strong `CLEARANCE_PASSWORD` and unique `SESSION_SECRET`.  
- Free public demos should keep password empty or use a throwaway demo password.
