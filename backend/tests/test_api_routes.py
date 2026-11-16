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
