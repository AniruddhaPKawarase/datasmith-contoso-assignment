"""Launch the FastAPI gateway on localhost:8001 with uvicorn.

Port 8001 (not 8000) so this doesn't collide with Project_dev's gateway.
Reads the worktree's .env — .env is gitignored, never touches Project_dev's.

Usage:
    .venv\\Scripts\\python.exe scripts\\serve_api.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

env_path = ROOT / ".env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# On Render/Fly/etc. POSTGRES_HOST is set by the platform. Only rewrite to
# localhost when we're running the local dev flow and .env had "postgres"
# (Docker-internal name) as the host.
if os.getenv("RENDER") is None and os.getenv("POSTGRES_HOST", "").lower() in {"", "postgres"}:
    os.environ["POSTGRES_HOST"] = "localhost"

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # Render sets $PORT; local dev falls back to 8001.
    port = int(os.getenv("PORT", os.getenv("CONTOSO_GATEWAY_PORT", "8001")))
    # 0.0.0.0 on prod (Render/Docker) so the platform can route traffic;
    # 127.0.0.1 locally to keep the gateway off the LAN.
    host = "0.0.0.0" if os.getenv("RENDER") or os.getenv("DOCKER") else "127.0.0.1"  # noqa: S104
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
