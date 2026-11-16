"""
Phase 3 SQL Analytics & Dimensional Modeling Test Suite.

Verifies:
1. Dimensional star schema structure (dim_date, dim_customers, dim_products, dim_sellers).
2. Fact tables (fact_orders, fact_order_items, fact_payments, fact_reviews).
3. Numerical baseline fidelity against Phase 1 discoveries:
   - Delivered GMV = R$ 13,221,498.11
   - Total Delivered Revenue = R$ 15,424,463.65
   - AOV = R$ 159.88
   - Unique Customers = 96,096
   - Repeat Rate = 3.12%
4. Approved analytical views accessible by the read-only agent user.
5. Verification of top product categories and seller performance metrics.
"""

import pytest
from sqlalchemy import text
from backend.app.services.database import readonly_engine

DIMENSIONS = ["dim_date", "dim_customers", "dim_products", "dim_sellers"]
FACTS = ["fact_orders", "fact_order_items", "fact_payments", "fact_reviews"]
ANALYTICAL_VIEWS = [
    "v_monthly_sales",
    "v_category_performance",
    "v_state_sales_distribution",
    "v_customer_rfm_segments",
    "v_seller_performance",
]


@pytest.mark.parametrize("dim_table", DIMENSIONS)
def test_dimension_tables_exist_and_populated(dim_table):
    """Verify dimension tables exist and are populated in analytics schema."""
    with readonly_engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM analytics.{dim_table};")).scalar()
        assert count > 0, f"Dimension table analytics.{dim_table} is empty"


@pytest.mark.parametrize("fact_table", FACTS)
def test_fact_tables_exist_and_populated(fact_table):
    """Verify fact tables exist and have expected record counts."""
    with readonly_engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM analytics.{fact_table};")).scalar()
        assert count > 0, f"Fact table analytics.{fact_table} is empty"


def test_delivered_revenue_baselines():
    """
    Verify delivered financial metrics match exact Phase 1 baselines:
    - Delivered GMV = 13,221,498.11
    - Delivered Revenue = 15,424,463.65
    - AOV = 159.88
    """
    query = text(
        """
        SELECT 
            ROUND(SUM(CASE WHEN is_delivered THEN total_item_value ELSE 0 END), 2) AS gmv,
            ROUND(SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END), 2) AS total_revenue,
            ROUND(
                SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END) / 
                NULLIF(COUNT(CASE WHEN is_delivered THEN 1 END), 0),
                2
            ) AS aov,
            COUNT(CASE WHEN is_delivered THEN 1 END) AS delivered_orders
        FROM analytics.fact_orders;
        """
    )
    with readonly_engine.connect() as conn:
        row = conn.execute(query).mappings().fetchone()
        assert float(row["gmv"]) == 13221498.11
        assert float(row["total_revenue"]) == 15424463.65
        assert float(row["aov"]) == 159.88
        assert row["delivered_orders"] == 96478


def test_customer_metrics_and_grain():
    """
    Verify customer metrics aggregate on customer_unique_id:
    - Unique Customers = 96,096
    - Repeat Purchase Rate = 3.12%
    """
    query = text(
        """
        WITH cust_orders AS (
            SELECT dc.customer_unique_id, COUNT(DISTINCT fo.order_id) AS order_cnt
            FROM analytics.fact_orders fo
            JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
            GROUP BY dc.customer_unique_id
        )
        SELECT 
            COUNT(*) AS unique_customers,
            COUNT(CASE WHEN order_cnt > 1 THEN 1 END) AS repeat_customers,
            ROUND(COUNT(CASE WHEN order_cnt > 1 THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100.0, 2) AS repeat_rate_pct
        FROM cust_orders;
        """
    )
    with readonly_engine.connect() as conn:
        row = conn.execute(query).mappings().fetchone()
        assert row["unique_customers"] == 96096
        assert row["repeat_customers"] == 2997
        assert float(row["repeat_rate_pct"]) == 3.12


@pytest.mark.parametrize("view_name", ANALYTICAL_VIEWS)
def test_analytical_views_accessible_by_readonly_user(view_name):
    """Verify that read-only user can query all approved analytical views without errors."""
    query = text(f"SELECT * FROM analytics.{view_name} LIMIT 5;")
    with readonly_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        assert len(rows) > 0, f"View analytics.{view_name} returned 0 rows"


def test_top_category_revenue():
    """Verify top revenue product category in v_category_performance."""
    query = text(
        """
        SELECT product_category, total_revenue 
        FROM analytics.v_category_performance 
        LIMIT 1;
        """
    )
    with readonly_engine.connect() as conn:
        row = conn.execute(query).mappings().fetchone()
        assert row["product_category"] in ("health_beauty", "beleza_saude")
        assert float(row["total_revenue"]) > 1000000.00


def test_zero_cartesian_inflation_in_fact_orders():
    """
    Verify that summing fact_orders.total_item_value for delivered orders
    matches summing fact_order_items.price directly with 0.00% error.
    """
    with readonly_engine.connect() as conn:
        orders_sum = conn.execute(
            text("SELECT ROUND(SUM(total_item_value), 2) FROM analytics.fact_orders WHERE is_delivered = TRUE;")
        ).scalar()
        items_sum = conn.execute(
            text("SELECT ROUND(SUM(price), 2) FROM analytics.fact_order_items WHERE is_delivered = TRUE;")
        ).scalar()

        assert float(orders_sum) == float(items_sum) == 13221498.11
