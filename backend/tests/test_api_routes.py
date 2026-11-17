"""
FastAPI Endpoints Integration Test Suite.
"""

import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "InsightIQ" in response.json()["service"]


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["database_connected"] is True
    assert data["ollama_connected"] is True


def test_api_kpi_summary():
    response = client.get("/api/kpi/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 15424463.65
    assert data["total_orders"] == 99441
    assert data["delivered_orders"] == 96478
    assert data["unique_customers"] == 96096


def test_api_kpi_monthly():
    response = client.get("/api/kpi/monthly")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 20
    assert "total_delivered_revenue" in data[0]


def test_api_anomalies_revenue():
    response = client.get("/api/anomalies/revenue")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Black Friday should be top anomaly
    assert data[0]["date"] == "2017-11-24"


def test_api_correlations_delivery():
    response = client.get("/api/correlations/delivery")
    assert response.status_code == 200
    data = response.json()
    assert "correlations" in data
    assert "comparative_cohorts" in data


def test_api_rag_status():
    response = client.get("/api/rag/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["vector_store"]["total_chunks"] >= 20
    assert data["llm_available"] is True


def test_api_rag_retrieve():
    payload = {
        "query": "What is the average order value?",
        "top_k": 3,
    }
    response = client.post("/api/rag/retrieve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 3
    assert len(data["citations"]) == 3
    sources = [c["source"] for c in data["citations"]]
    assert "metric_definitions.md" in sources


def test_api_rag_query():
    payload = {
        "question": "What is the definition of average order value?",
        "top_k": 2,
    }
    response = client.post("/api/rag/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["answer"]) > 20
    assert data["is_grounded"] is True
    assert len(data["citations"]) >= 1


def test_api_agent_tools():
    response = client.get("/api/agent/tools")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    tool_names = [t["name"] for t in data]
    assert "sql_analytics_tool" in tool_names
    assert "rag_retrieval_tool" in tool_names
    assert "python_analytics_tool" in tool_names


def test_api_agent_query():
    payload = {
        "question": "What is our delivered revenue and how is it defined?",
        "mode_override": "hybrid",
        "top_k": 2,
    }
    response = client.post("/api/agent/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["final_answer"]) > 20
    assert len(data["execution_steps"]) >= 3
    assert "rag_retrieval_tool" in data["tools_used"]
    assert "sql_analytics_tool" in data["tools_used"]


def test_api_investigation_run():
    payload = {
        "investigation_type": "satisfaction_drivers"
    }
    response = client.post("/api/investigation/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "pearson_r" in data["metrics"]
    assert len(data["evidence_data"]) > 0


def test_api_reports_executive():
    response = client.get("/api/reports/executive")
    assert response.status_code == 200
    data = response.json()
    assert "InsightIQ Executive Business Performance Report" in data["markdown"]
    assert "Total Delivered Revenue" in data["markdown"]
    assert len(data["sections"]) >= 4




