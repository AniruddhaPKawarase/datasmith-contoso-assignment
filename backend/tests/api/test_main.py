"""FastAPI gateway smoke tests — verifies request/response shape only.

These tests instantiate the app but do not run a real LLM call; they
only check the HTTP contract (request validation + healthz shape).
The full integration test is the live demo (scripts/midsem_demo.py).
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_ask_request_validation_empty_query():
    """Empty query must be rejected by Pydantic."""
    from app.api.main import app

    with TestClient(app) as client:
        resp = client.post("/ask", json={"query": "", "session_id": "s1"})
    assert resp.status_code == 422


def test_ask_request_validation_missing_session_id():
    """Missing session_id must be rejected."""
    from app.api.main import app

    with TestClient(app) as client:
        resp = client.post("/ask", json={"query": "How many products?"})
    assert resp.status_code == 422


def test_healthz_shape():
    """/healthz returns ok+tables shape."""
    from app.api.main import app

    with TestClient(app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "tables" in body
    assert "sessions" in body
