"""
Customer Analytics & RFM Segmentation Service for InsightIQ.

Performs:
- Customer RFM (Recency, Frequency, Monetary) breakdown and value contributions.
- Customer cohort retention analysis (tracking monthly acquisition cohorts over time).
- Identification and profiling of top high-value customer accounts.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.database import readonly_engine


class CustomerAnalyticsService:
    """Provides customer behavior analysis, cohort retention, and RFM metrics."""

    @staticmethod
    def get_rfm_summary() -> pd.DataFrame:
        """Retrieves and summarizes customer segments by customer count and monetary contribution."""
        query = text(
            """
            SELECT
                customer_segment,
                COUNT(*) AS customer_count,
                ROUND(SUM(monetary), 2) AS total_revenue,
                ROUND(AVG(monetary), 2) AS avg_monetary,
                ROUND(AVG(frequency), 2) AS avg_frequency,
                ROUND(AVG(recency_days), 1) AS avg_recency_days
            FROM analytics.v_customer_rfm_segments
            GROUP BY customer_segment
            ORDER BY total_revenue DESC;
            """
        )
        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn)

        total_customers = df["customer_count"].sum()
        total_revenue = df["total_revenue"].sum()

        df["customer_pct"] = (df["customer_count"] / total_customers * 100.0).round(2)
        df["revenue_pct"] = (df["total_revenue"] / total_revenue * 100.0).round(2)

        return df

    @staticmethod
    def get_cohort_retention_matrix(min_cohort_size: int = 100) -> pd.DataFrame:
        """
        Calculates monthly cohort retention rates.
        Groups unique customers by the month of their first order and tracks repeat orders in subsequent months.
        """
        query = text(
            """
            WITH customer_orders AS (
                SELECT
                    dc.customer_unique_id,
                    fo.order_id,
                    fo.order_purchase_timestamp,
                    DATE_TRUNC('month', fo.order_purchase_timestamp)::DATE AS order_month
                FROM analytics.fact_orders fo
                JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
                WHERE fo.is_delivered = TRUE
            ),
            customer_cohorts AS (
                SELECT
                    customer_unique_id,
                    MIN(order_month) AS cohort_month
                FROM customer_orders
                GROUP BY customer_unique_id
            ),
            cohort_activity AS (
                SELECT
                    cc.cohort_month,
                    co.order_month,
                    (EXTRACT(YEAR FROM co.order_month) - EXTRACT(YEAR FROM cc.cohort_month)) * 12 +
                    (EXTRACT(MONTH FROM co.order_month) - EXTRACT(MONTH FROM cc.cohort_month)) AS period_number,
                    COUNT(DISTINCT co.customer_unique_id) AS active_customers
                FROM customer_orders co
                JOIN customer_cohorts cc ON co.customer_unique_id = cc.customer_unique_id
                GROUP BY cc.cohort_month, co.order_month
            )
            SELECT
                TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
                period_number,
                active_customers
            FROM cohort_activity
            ORDER BY cohort_month, period_number;
            """
        )
        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn)

        # Pivot into matrix (cohort rows x period columns)
        pivot = df.pivot(index="cohort", columns="period_number", values="active_customers").fillna(0)
        
        # Calculate retention percentages relative to month 0
        cohort_sizes = pivot[0]
        retention_pct = pivot.divide(cohort_sizes, axis=0) * 100.0
        retention_pct = retention_pct.round(2)

        return retention_pct

    @staticmethod
    def get_top_customers(limit: int = 15) -> pd.DataFrame:
        """Retrieves highest-value customer accounts across platform history."""
        query = text(
            f"""
            SELECT
                dc.customer_unique_id,
                MAX(dc.customer_city) AS city,
                MAX(dc.customer_state) AS state,
                COUNT(DISTINCT fo.order_id) AS order_count,
                ROUND(SUM(fo.total_order_amount), 2) AS total_spend,
                ROUND(AVG(fo.total_order_amount), 2) AS avg_order_value,
                ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score
            FROM analytics.fact_orders fo
            JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
            WHERE fo.is_delivered = TRUE
            GROUP BY dc.customer_unique_id
            ORDER BY total_spend DESC
            LIMIT {limit};
            """
        )
        with readonly_engine.connect() as conn:
            return pd.read_sql(query, conn)


if __name__ == "__main__":
    service = CustomerAnalyticsService()
    rfm = service.get_rfm_summary()
    print("RFM Summary Table:")
    print(rfm[["customer_segment", "customer_count", "customer_pct", "total_revenue", "revenue_pct"]])
    
    top = service.get_top_customers(3)
    print("\nTop 3 Customers:")
    print(top[["customer_unique_id", "state", "order_count", "total_spend"]])

