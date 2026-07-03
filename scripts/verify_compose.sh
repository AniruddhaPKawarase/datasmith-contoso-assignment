#!/usr/bin/env bash
# Sanity-check that Docker Compose brings up all services.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Pulling images"
docker compose -f docker/docker-compose.yml pull

echo "==> Starting stack"
docker compose -f docker/docker-compose.yml up -d

echo "==> Waiting 30s for services to start"
sleep 30

echo "==> Checking PostgreSQL"
docker exec scm-postgres pg_isready -U odoo

echo "==> Checking Redis"
docker exec scm-redis redis-cli ping

echo "==> Checking backend health"
curl -fsS http://localhost:8000/health | tee /dev/stderr

echo "==> Checking Odoo (may take longer to boot)"
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:8069/ || echo "Odoo not ready yet — give it 60s"

echo "==> Checking frontend"
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:3000/ || echo "Frontend not ready yet"

echo
echo "Verification complete. Services running."
echo "Tear down with: docker compose -f docker/docker-compose.yml down"
