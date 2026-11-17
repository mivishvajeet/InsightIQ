"""
Comprehensive Test Suite for InsightIQ Orchestrator Agent and Tools.

Tests:
1. ToolRegistry registration, listing, and dynamic dispatching
2. SQLAnalyticsTool safety, execution, and structured outputs
3. RAGRetrievalTool semantic search, citations, and answer synthesis
4. PythonAnalyticsTool statistical operations (KPIs, anomalies, correlations)
5. AgentIntentClassifier taxonomy and planning rules
6. OrchestratorAgent multi-step workflow execution, step traces, and mode overrides
"""

import pytest
from backend.app.tools.registry import tool_registry
from backend.app.tools.sql_tool import SQLAnalyticsTool
from backend.app.tools.rag_tool import RAGRetrievalTool
from backend.app.tools.python_tool import PythonAnalyticsTool
from backend.app.agents.intent_classifier import AgentIntentClassifier
from backend.app.agents.orchestrator import OrchestratorAgent, orchestrator_agent


def test_tool_registry_registration_and_listing():
    """Verify that all three core analytical tools are registered."""
    tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "sql_analytics_tool" in tool_names
    assert "rag_retrieval_tool" in tool_names
    assert "python_analytics_tool" in tool_names


def test_sql_analytics_tool_execution():
    """Verify that the SQL tool validates and executes queries against PostgreSQL."""
    tool = SQLAnalyticsTool()
    output = tool.run(question="What is total revenue?", sql="SELECT total_delivered_revenue FROM analytics.v_monthly_sales LIMIT 2;")
    assert output.success is True
    assert output.row_count == 2
    assert "total_delivered_revenue" in output.columns
    assert len(output.data) == 2
    assert output.error is None


def test_rag_retrieval_tool_execution():
    """Verify that the RAG tool retrieves knowledge chunks and returns citations."""
    tool = RAGRetrievalTool()
    output = tool.run(query="What is the definition of average order value?", top_k=2, synthesize_answer=False)
    assert output.success is True
    assert output.total_found > 0
    assert len(output.citations) > 0
    assert output.citations[0]["source"].endswith(".md")


def test_python_analytics_tool_operations():
    """Verify that the Python analytics tool runs KPI, anomaly, and correlation operations."""
    tool = PythonAnalyticsTool()

    # 1. Executive Summary
    kpi_out = tool.run("executive_summary")
    assert kpi_out.success is True
    assert float(kpi_out.metrics["total_revenue"]) == 15424463.65

    # 2. Revenue Anomalies
    anom_out = tool.run("revenue_anomalies", {"top_n": 5})
    assert anom_out.success is True
    assert len(anom_out.data) > 0
    assert anom_out.data[0]["date"] == "2017-11-24"  # Black Friday

    # 3. Delivery Correlation
    corr_out = tool.run("delivery_correlation")
    assert corr_out.success is True
    assert corr_out.metrics["pearson_r"] < -0.20
    assert "Correlation does not imply causation" in corr_out.summary or "does not establish causality" in corr_out.summary


def test_agent_intent_classifier():
    """Verify accurate classification of SQL, RAG, Python, and Hybrid intents."""
    classifier = AgentIntentClassifier()

    cases = [
        ("What is the monthly revenue trend?", "sql"),
        ("Which product category generates the highest sales?", "sql"),
        ("What is the definition of average order value?", "rag"),
        ("How is customer retention calculated?", "rag"),
        ("Detect statistical revenue anomalies and spikes", "python"),
        ("Calculate Pearson correlation between delivery delay and review score", "python"),
        ("What is customer RFM segmentation?", "python"),
        ("What does customer retention mean and how many repeat customers do we actually have?", "hybrid"),
    ]

    for q, expected_intent in cases:
        result = classifier.classify(q)
        assert result.intent == expected_intent, f"Failed on '{q}': expected '{expected_intent}', got '{result.intent}'"


def test_orchestrator_agent_workflow_execution():
    """Verify end-to-end multi-step orchestration on a business question."""
    agent = OrchestratorAgent()
    result = agent.run("What is the monthly revenue trend?")

    assert result.question == "What is the monthly revenue trend?"
    assert result.intent == "sql"
    assert "sql_analytics_tool" in result.tools_used
    assert len(result.execution_steps) >= 3  # Plan, Tool, Synthesize
    assert len(result.final_answer) > 20
    assert result.sql_query is not None
    assert len(result.data_table) > 0


def test_orchestrator_agent_mode_override():
    """Verify that mode_override forces a specific tool execution path."""
    agent = OrchestratorAgent()
    result = agent.run("Tell me about our performance", mode_override="python")

    assert result.intent == "python"
    assert "python_analytics_tool" in result.tools_used
    assert "sql_analytics_tool" not in result.tools_used
    assert len(result.execution_steps) >= 3

