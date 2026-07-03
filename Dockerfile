# SCM-Contoso backend — Render / Fly-friendly image.
# ponytail: single-stage. If we ever cache-hit sensitivity matters we'll
# split builder + runtime, but the wheel install is already tiny.

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: only what psycopg[binary] and duckdb need for wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements — copy first for layer cache.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# App code + schema cache + startup script.
COPY backend /app/backend
COPY scripts /app/scripts

ENV PYTHONPATH=/app/backend \
    CONTOSO_SCHEMA_PATH=/app/backend/data/contoso_schema.json \
    PORT=8001

EXPOSE 8001

# Render passes the port via $PORT; scripts/serve_api.py already reads it.
CMD ["python", "scripts/serve_api.py"]
