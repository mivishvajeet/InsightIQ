"""
InsightIQ FastAPI Application Backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import router
from backend.app.api.schemas import HealthResponse
from backend.app.services.database import test_connections
from backend.app.services.llm_client import OllamaClient

app = FastAPI(
    title="InsightIQ API",
    description="Agentic Business Intelligence Platform REST API",
    version="1.0.0",
)

# CORS middleware for local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Healthcheck endpoint checking PostgreSQL and Ollama readiness."""
    db_status = test_connections().get("admin", False)
    ollama_status = OllamaClient().is_available()
    return HealthResponse(
        status="ok" if db_status and ollama_status else "degraded",
        database_connected=db_status,
        ollama_connected=ollama_status,
    )


@app.get("/")
def root():
    return {
        "service": "InsightIQ Business Intelligence API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }
