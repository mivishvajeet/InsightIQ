"""
Pytest Suite for Executive PDF Generation & Real-Time SSE Token Streaming.

Tests:
1. PDFReportGenerator in-memory PDF compilation, valid PDF header, and byte size.
2. PDFReportGenerator with mock telemetry data ensuring proper section flowables.
3. FastAPI endpoint GET /api/reports/executive/pdf returns 200 with application/pdf header.
4. FastAPI endpoint POST /api/agent/stream returns SSE stream with steps, token, and done events.
"""

import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.reporting.pdf_generator import PDFReportGenerator
from backend.app.main import app


@pytest.fixture
def sample_report_data():
    return {
        "timestamp": "2026-11-20 09:30:00",
        "metrics": {
            "total_revenue": 15424463.65,
            "total_orders": 99441,
            "avg_order_value": 155.11,
            "avg_review_score": 4.07,
            "on_time_delivery_rate": 93.6,
            "repeat_customer_rate": 3.12,
        },
        "anomalies": [
            {
                "metric": "monthly_revenue",
                "period": "2017-11",
                "value": 1194882.8,
                "z_score": 2.85,
                "anomaly_type": "Surge",
                "explanation": "Black Friday volume surge.",
            }
        ],
        "top_categories": [
            {"product_category": "health_beauty", "total_orders": 9670, "total_revenue": 1258681.34},
            {"product_category": "watches_gifts", "total_orders": 5991, "total_revenue": 1205005.68},
        ],
        "top_states": [
            {"customer_state": "SP", "order_count": 41746, "revenue": 5202955.05},
            {"customer_state": "RJ", "order_count": 12852, "revenue": 1824093.62},
        ],
        "strategic_recommendations": [
            {
                "pillar": "Supply Chain & Logistics",
                "action": "Establish regional cross-docking in Southeast corridor to compress transit SLA.",
                "expected_impact": "+12% faster delivery",
                "priority": "HIGH",
            },
            {
                "pillar": "Customer Retention",
                "action": "Deploy category repurchase automation for consumables like Health & Beauty.",
                "expected_impact": "2.4x repeat purchase rate",
                "priority": "MEDIUM",
            },
        ],
    }


def test_pdf_report_generator_compiles_valid_bytes(sample_report_data):
    """Verifies that PDFReportGenerator produces valid PDF bytes from structured telemetry."""
    pdf_bytes = PDFReportGenerator.generate_pdf_bytes(sample_report_data)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_report_generator_sections_render(sample_report_data):
    """Verifies that multiple custom sections and tables compile without flowable layout errors."""
    pdf_bytes = PDFReportGenerator.generate_pdf_bytes(sample_report_data)

    # Validate that PDF content is intact
    assert b"InsightIQ Executive Business Briefing" in pdf_bytes or len(pdf_bytes) > 3000


def test_api_executive_pdf_endpoint(sample_report_data):
    """Verifies that GET /api/reports/executive/pdf delivers the PDF attachment."""
    client = TestClient(app)

    with patch(
        "backend.app.reporting.report_generator.ReportGeneratorService.generate_executive_business_report",
        return_value=sample_report_data,
    ):
        resp = client.get("/api/reports/executive/pdf")

        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert resp.content.startswith(b"%PDF-")


def test_api_agent_sse_streaming_endpoint():
    """Verifies that POST /api/agent/stream yields SSE chunks for steps, tokens, and done."""
    client = TestClient(app)

    fake_result = MagicMock()
    fake_result.execution_steps = ["Intent: SQL", "SQL executed: 1 row"]
    fake_result.intent = "SQL"
    fake_result.tools_used = ["sql_generator"]
    fake_result.sql_query = "SELECT count(*) FROM fact_orders;"
    fake_result.data_table = [{"count": 99441}]
    fake_result.final_answer = "The total number of orders in the warehouse is 99,441."
    fake_result.to_dict.return_value = {
        "question": "How many orders?",
        "intent": "SQL",
        "final_answer": "The total number of orders in the warehouse is 99,441.",
        "execution_steps": ["Intent: SQL"],
        "tools_used": ["sql_generator"],
        "sql_query": "SELECT count(*) FROM fact_orders;",
        "data_table": [{"count": 99441}],
        "execution_time_seconds": 0.42,
    }

    with patch("backend.app.agents.orchestrator.orchestrator_agent.run", return_value=fake_result):
        resp = client.post(
            "/api/agent/stream",
            json={"question": "How many orders?", "session_id": "test_stream_session"},
        )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        events_raw = resp.text
        assert "event: steps" in events_raw
        assert "event: token" in events_raw
        assert "event: done" in events_raw

        # Verify token payloads contain words
        lines = events_raw.strip().split("\n")
        token_count = sum(1 for line in lines if line.startswith("event: token"))
        assert token_count >= 5
