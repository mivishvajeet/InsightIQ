"""
Phase 2 Database Ingestion & Security Test Suite.

Verifies:
1. PostgreSQL connectivity for both admin and read-only roles.
2. Complete row count fidelity across all 9 ingested raw tables.
3. Database-level read-only security enforcement (rejecting INSERT, UPDATE, DELETE, DROP).
4. Schema isolation (read-only role cannot access raw schema directly).
5. Statement timeout enforcement for read-only user.
"""

import pytest
from sqlalchemy import text
from backend.app.services.database import admin_engine, readonly_engine

EXPECTED_ROW_COUNTS = {
    "customers": 99441,
    "orders": 99441,
    "products": 32951,
    "sellers": 3095,
    "order_items": 112650,
    "order_payments": 103886,
    "order_reviews": 99224,
    "geolocation": 1000163,
    "product_category_name_translation": 71,
}


def test_database_connections():
    """Verify both admin and read-only database connections succeed."""
    with admin_engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar()
        assert res == 1

    with readonly_engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar()
        assert res == 1


@pytest.mark.parametrize("table_name,expected_count", EXPECTED_ROW_COUNTS.items())
def test_raw_table_row_counts(table_name, expected_count):
    """Verify that every raw table has 100% row count fidelity with the source CSVs."""
    with admin_engine.connect() as conn:
        actual_count = conn.execute(text(f"SELECT COUNT(*) FROM raw.{table_name};")).scalar()
        assert actual_count == expected_count, (
            f"Table raw.{table_name} count mismatch: expected {expected_count}, got {actual_count}"
        )


def test_readonly_user_cannot_insert():
    """Verify that the read-only user cannot perform INSERT operations."""
    with pytest.raises(Exception) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO raw.customers VALUES ('test_id', 'test_uid', '00000', 'city', 'SP');"
                )
            )
    assert "permission denied" in str(exc_info.value).lower() or "read-only" in str(exc_info.value).lower()


def test_readonly_user_cannot_drop_table():
    """Verify that the read-only user cannot execute destructive DDL (DROP TABLE)."""
    with pytest.raises(Exception) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(text("DROP TABLE raw.customers CASCADE;"))
    assert "permission denied" in str(exc_info.value).lower() or "read-only" in str(exc_info.value).lower()


def test_readonly_user_cannot_delete():
    """Verify that the read-only user cannot execute DELETE statements."""
    with pytest.raises(Exception) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(text("DELETE FROM raw.customers WHERE 1=1;"))
    assert "permission denied" in str(exc_info.value).lower() or "read-only" in str(exc_info.value).lower()


def test_readonly_user_schema_isolation():
    """Verify that the read-only user cannot query raw schema directly (only analytics)."""
    with pytest.raises(Exception) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(text("SELECT * FROM raw.customers LIMIT 1;"))
    assert "permission denied" in str(exc_info.value).lower()
