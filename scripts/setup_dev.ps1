# Local dev setup for Windows PowerShell. Run from project root.
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Host "==> Copying .env.example to .env (skip if exists)"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "==> Backend: creating venv + installing"
Set-Location "$ROOT/backend"
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

Write-Host "==> Frontend: installing"
Set-Location "$ROOT/frontend"
npm install

Write-Host "==> Pre-commit: installing hooks"
Set-Location $ROOT
pip install pre-commit
pre-commit install

Write-Host ""
Write-Host "Setup complete. Next steps:" -ForegroundColor Green
Write-Host "  1) Edit .env and set OPENROUTER_API_KEY"
Write-Host "  2) docker compose -f docker/docker-compose.yml up -d"
Write-Host "  3) backend tests:  cd backend; pytest"
Write-Host "  4) frontend dev:   cd frontend; npm run dev"
