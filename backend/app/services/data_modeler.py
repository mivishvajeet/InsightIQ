"""
Data Modeler Service for InsightIQ.

Executes and manages the analytical dimensional modeling pipeline:
1. database/staging/01_staging_views.sql (Cleansed staging views)
2. database/marts/01_dimensions.sql (dim_date, dim_customers, dim_products, dim_sellers)
3. database/marts/02_facts.sql (fact_orders, fact_order_items, fact_payments, fact_reviews)
4. database/marts/03_analytical_views.sql (v_monthly_sales, v_category_performance, etc.)
5. Security grants for insightiq_readonly
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from backend.app.services.database import admin_engine


class DataModeler:
    """Manages the creation and verification of staging views and dimensional marts."""

    def __init__(self, base_dir: Path = Path("database")):
        self.base_dir = Path(base_dir)

    def execute_sql_file(self, file_path: Path):
        """Executes a SQL script file against the PostgreSQL database."""
        print(f"  Executing {file_path.name} ...")
        start_time = time.time()
        with open(file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        with admin_engine.connect() as conn:
            conn.execute(text(sql_script))
            conn.commit()
        elapsed = time.time() - start_time
        print(f"  [DONE] {file_path.name} executed in {elapsed:.2f}s")

    def build_marts(self) -> Dict[str, Any]:
        """Runs the entire dimensional modeling transformation pipeline."""
        start_total = time.time()
        print("Starting InsightIQ Data Modeling & Mart Construction...")

        steps = [
            self.base_dir / "staging" / "01_staging_views.sql",
            self.base_dir / "marts" / "01_dimensions.sql",
            self.base_dir / "marts" / "02_facts.sql",
            self.base_dir / "marts" / "03_analytical_views.sql",
        ]

        for step_path in steps:
            if not step_path.exists():
                raise FileNotFoundError(f"Missing modeling script: {step_path}")
            self.execute_sql_file(step_path)

        total_elapsed = time.time() - start_total
        print(f"\nAll dimensional marts successfully constructed in {total_elapsed:.2f}s!")
        return self.verify_marts()

    def verify_marts(self) -> Dict[str, Any]:
        """Runs validation checks on the populated dimensional tables and views."""
        results = {}
        with admin_engine.connect() as conn:
            # 1. Row counts
            tables = [
                "dim_date",
                "dim_customers",
                "dim_products",
                "dim_sellers",
                "fact_orders",
                "fact_order_items",
                "fact_payments",
                "fact_reviews",
            ]
            counts = {}
            for t in tables:
                counts[t] = conn.execute(text(f"SELECT COUNT(*) FROM analytics.{t};")).scalar()
            results["table_counts"] = counts

            # 2. Financial baselines
            baselines_query = text(
                """
                SELECT 
                    ROUND(SUM(CASE WHEN is_delivered THEN total_item_value ELSE 0 END), 2) AS delivered_gmv,
                    ROUND(SUM(CASE WHEN is_delivered THEN total_freight_value ELSE 0 END), 2) AS delivered_freight,
                    ROUND(SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END), 2) AS delivered_revenue,
                    ROUND(
                        SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END) / 
                        NULLIF(COUNT(CASE WHEN is_delivered THEN 1 END), 0),
                        2
                    ) AS delivered_aov,
                    COUNT(DISTINCT customer_id) AS total_orders,
                    COUNT(CASE WHEN is_delivered THEN 1 END) AS delivered_orders
                FROM analytics.fact_orders;
                """
            )
            row = conn.execute(baselines_query).mappings().fetchone()
            results["financial_baselines"] = dict(row)

            # 3. Unique customers & repeat rate
            cust_query = text(
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
            cust_row = conn.execute(cust_query).mappings().fetchone()
            results["customer_metrics"] = dict(cust_row)

        return results


if __name__ == "__main__":
    modeler = DataModeler()
    verification = modeler.build_marts()
    print("\n=== MART VERIFICATION RESULTS ===")
    for k, v in verification.items():
        print(f"\n{k.upper()}:")
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                print(f"  {sub_k:30s}: {sub_v}")
        else:
            print(f"  {v}")

