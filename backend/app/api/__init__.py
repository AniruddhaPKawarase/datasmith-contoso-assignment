"""HTTP gateway exposing the Orchestrator over FastAPI."""
from app.api.main import app

__all__ = ["app"]
