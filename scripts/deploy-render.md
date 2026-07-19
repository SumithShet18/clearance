# Deploy Clearance to Render (free HTTPS)

## Option A — One-click Blueprint (recommended)

1. Sign in at https://dashboard.render.com (GitHub login works).
2. Open:  
   **https://render.com/deploy?repo=https://github.com/SumithShet18/clearance**
3. Connect the `SumithShet18/clearance` repo if prompted.
4. Click **Apply** / **Deploy Blueprint**.
5. Wait for build (Docker). Health check: `/api/health`.
6. Your URL will look like: `https://clearance-xxxx.onrender.com`

Free tier spins down after idle; first request may take ~30–60s.

## Option B — Dashboard Web Service

1. **New → Web Service**
2. Connect GitHub → `SumithShet18/clearance`
3. Runtime: **Docker**
4. Dockerfile path: `./Dockerfile`
5. Plan: **Free**
6. Health check path: `/api/health`
7. Env: `CLEARANCE_MODE=mock`

## Option C — API (if you have a Render API key)

```powershell
$env:RENDER_API_KEY = "rnd_..."
# then run scripts/create-render-service.ps1 when available
```

Create a key: Dashboard → Account Settings → API Keys.
