# One-click local demo seed + metrics
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
Write-Host "Seeding demo cases..." -ForegroundColor Cyan
$seed = Invoke-RestMethod -Method POST "$base/api/demo/seed"
Write-Host "Seeded $($seed.seeded) cases"
$metrics = Invoke-RestMethod "$base/api/cases/metrics/summary"
$eval = Invoke-RestMethod "$base/api/evals/run"
Write-Host "Auto-resolve rate: $([math]::Round($metrics.auto_resolve_rate*100,1))%"
Write-Host "Needs review: $($metrics.needs_review)"
Write-Host "Gold field accuracy: $([math]::Round($eval.field_accuracy*100,1))%"
Write-Host "Open $base" -ForegroundColor Green
