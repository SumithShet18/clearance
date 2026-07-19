# Start Clearance API + UI
Set-Location $PSScriptRoot\..\apps\api
if (-not (Test-Path .venv)) {
  python -m venv .venv
  .\.venv\Scripts\python -m pip install -r requirements.txt
}
Write-Host "Clearance → http://127.0.0.1:8000" -ForegroundColor Cyan
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
