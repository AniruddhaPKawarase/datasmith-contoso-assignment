#!/usr/bin/env bash
# Local dev setup. Run from project root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Copying .env.example to .env (skip if exists)"
[ -f .env ] || cp .env.example .env

echo "==> Backend: creating venv + installing"
cd "$ROOT/backend"
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate || source .venv/Scripts/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo "==> Frontend: installing"
cd "$ROOT/frontend"
npm install

echo "==> Pre-commit: installing hooks"
cd "$ROOT"
pip install pre-commit
pre-commit install

echo
echo "Setup complete. Next steps:"
echo "  1) Edit .env and set OPENROUTER_API_KEY"
echo "  2) docker compose -f docker/docker-compose.yml up -d"
echo "  3) backend tests:  cd backend && pytest"
echo "  4) frontend dev:   cd frontend && npm run dev"
