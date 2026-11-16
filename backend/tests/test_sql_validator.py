"""
Unit tests for SQLValidator security and AST validation rules.
"""

import pytest
from backend.app.services.sql_generator import SQLValidator


def test_sanitize_sql_markdown_stripping():
    raw = "```sql\nSELECT * FROM analytics.v_monthly_sales;\n```"
    cleaned = SQLValidator.sanitize_sql(raw)
    assert cleaned == "SELECT * FROM analytics.v_monthly_sales"


def test_validate_valid_select():
    sql = "SELECT * FROM analytics.fact_orders WHERE is_delivered = TRUE"
    is_valid, err = SQLValidator.validate_sql(sql)
    assert is_valid is True
    assert err is None


def test_validate_valid_with_select():
    sql = "WITH monthly AS (SELECT year_month, total_delivered_revenue FROM analytics.v_monthly_sales) SELECT * FROM monthly"
    is_valid, err = SQLValidator.validate_sql(sql)
    assert is_valid is True
    assert err is None


@pytest.mark.parametrize(
    "destructive_sql",
    [
        "DROP TABLE analytics.fact_orders CASCADE;",
        "DELETE FROM analytics.dim_customers WHERE 1=1;",
        "UPDATE analytics.fact_orders SET total_order_amount = 0;",
        "INSERT INTO analytics.fact_orders VALUES ('1', '2');",
        "TRUNCATE analytics.fact_orders;",
        "ALTER TABLE analytics.fact_orders DROP COLUMN order_id;",
    ],
)
def test_validate_rejects_destructive_keywords(destructive_sql):
    is_valid, err = SQLValidator.validate_sql(destructive_sql)
    assert is_valid is False
    assert "rejected" in err.lower()


def test_validate_rejects_raw_and_staging_access():
    sql_raw = "SELECT * FROM raw.customers LIMIT 10"
    is_valid, err = SQLValidator.validate_sql(sql_raw)
    assert is_valid is False
    assert "prohibited" in err.lower()

    sql_stg = "SELECT * FROM staging.stg_orders LIMIT 10"
    is_valid, err = SQLValidator.validate_sql(sql_stg)
    assert is_valid is False
    assert "prohibited" in err.lower()


def test_validate_rejects_stacked_queries():
    stacked = "SELECT * FROM analytics.fact_orders; DROP TABLE analytics.dim_sellers;"
    is_valid, err = SQLValidator.validate_sql(stacked)
    assert is_valid is False
    assert "multiple" in err.lower() or "rejected" in err.lower()


def test_enforce_limit_injection():
    sql = "SELECT * FROM analytics.fact_orders"
    limited = SQLValidator.enforce_limit(sql, default_limit=500)
    assert limited.endswith("LIMIT 500")

    already_limited = "SELECT * FROM analytics.fact_orders LIMIT 25"
    not_modified = SQLValidator.enforce_limit(already_limited, default_limit=500)
    assert not_modified == already_limited

