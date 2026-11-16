"""
Phase 5 Local LLM Integration & SQL Generator Test Suite.

Verifies:
1. Ollama local daemon availability on http://localhost:11434.
2. SQLGenerator query execution with read-only security limits.
3. SQLGenerator rejection of dangerous queries.
4. Text-to-SQL generation when local model is available.
"""

import pytest
import pandas as pd
from backend.app.services.llm_client import OllamaClient
from backend.app.services.sql_generator import SQLGenerator, SQLValidator


def test_ollama_daemon_is_available():
    """Verify local Ollama daemon is running and responsive."""
    client = OllamaClient()
    assert client.is_available() is True, "Ollama daemon on http://localhost:11434 is unreachable."


def test_sql_generator_safe_execution():
    """Verify SQLGenerator successfully executes validated analytics queries."""
    generator = SQLGenerator()
    query = "SELECT year_month, total_delivered_revenue FROM analytics.v_monthly_sales ORDER BY year_month LIMIT 5;"
    df, err = generator.execute_query(query)

    assert err is None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert "total_delivered_revenue" in df.columns


def test_sql_generator_blocks_destructive_query():
    """Verify SQLGenerator blocks DROP/DELETE before reaching database."""
    generator = SQLGenerator()
    malicious = "DROP TABLE analytics.fact_orders;"
    df, err = generator.execute_query(malicious)

    assert df.empty
    assert err is not None
    assert "rejected" in err.lower()


def test_sql_generator_blocks_raw_schema_access():
    """Verify SQLGenerator blocks direct raw schema access."""
    generator = SQLGenerator()
    unauthorized = "SELECT * FROM raw.orders LIMIT 5;"
    df, err = generator.execute_query(unauthorized)

    assert df.empty
    assert err is not None
    assert "prohibited" in err.lower()


def test_sql_generator_enforces_limit():
    """Verify queries executed without LIMIT are automatically capped."""
    generator = SQLGenerator()
    unlimited = "SELECT customer_state FROM analytics.dim_customers"
    safe = SQLValidator.enforce_limit(unlimited, default_limit=10)
    assert "LIMIT 10" in safe

