"""
KPI Calculation & Period-over-Period Comparison Service for InsightIQ.

Calculates:
- High-level executive KPIs (Revenue, GMV, Orders, AOV, Unique Customers, Repeat Rate, Avg Review).
- Period comparisons: Month-over-Month (MoM) and Year-over-Year (YoY) percentage changes.
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


class KPIService:
    """Computes executive KPIs and temporal growth metrics from analytics marts."""

    @staticmethod
    def get_executive_summary() -> Dict[str, Any]:
        """Calculates headline platform metrics across delivered orders."""
        query = text(
            """
            SELECT
                ROUND(SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END), 2) AS total_revenue,
                ROUND(SUM(CASE WHEN is_delivered THEN total_item_value ELSE 0 END), 2) AS total_gmv,
                ROUND(SUM(CASE WHEN is_delivered THEN total_freight_value ELSE 0 END), 2) AS total_freight,
                COUNT(DISTINCT order_id) AS total_orders,
                COUNT(CASE WHEN is_delivered THEN 1 END) AS delivered_orders,
                ROUND(
                    SUM(CASE WHEN is_delivered THEN total_order_amount ELSE 0 END) / 
                    NULLIF(COUNT(CASE WHEN is_delivered THEN 1 END), 0), 
                    2
                ) AS aov,
                ROUND(AVG(latest_review_score), 2) AS avg_review_score,
                ROUND(AVG(CASE WHEN is_delivered THEN delivery_lead_time_days END), 1) AS avg_delivery_days,
                ROUND(
                    COUNT(CASE WHEN is_delivered AND is_on_time = TRUE THEN 1 END)::NUMERIC / 
                    NULLIF(COUNT(CASE WHEN is_delivered AND delivery_delay_days IS NOT NULL THEN 1 END), 0)::NUMERIC * 100.0,
                    2
                ) AS on_time_rate_pct
            FROM analytics.fact_orders;
            """
        )

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
                ROUND(COUNT(CASE WHEN order_cnt > 1 THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100.0, 2) AS repeat_purchase_rate_pct
            FROM cust_orders;
            """
        )

        with readonly_engine.connect() as conn:
            exec_row = conn.execute(query).mappings().fetchone()
            cust_row = conn.execute(cust_query).mappings().fetchone()

        result = dict(exec_row)
        result.update(dict(cust_row))
        return result

    @staticmethod
    def get_monthly_growth_trend() -> pd.DataFrame:
        """Retrieves monthly sales and computes MoM growth percentages."""
        query = text(
            """
            SELECT
                year_month,
                year,
                month,
                delivered_orders,
                gmv,
                freight_revenue,
                total_delivered_revenue,
                aov,
                active_unique_customers
            FROM analytics.v_monthly_sales
            ORDER BY year_month;
            """
        )
        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn)

        # Calculate Month-over-Month (MoM) growth rates
        df["revenue_mom_pct"] = df["total_delivered_revenue"].pct_change() * 100.0
        df["orders_mom_pct"] = df["delivered_orders"].pct_change() * 100.0
        df["aov_mom_pct"] = df["aov"].pct_change() * 100.0

        # Round values for presentation
        df["revenue_mom_pct"] = df["revenue_mom_pct"].round(2)
        df["orders_mom_pct"] = df["orders_mom_pct"].round(2)
        df["aov_mom_pct"] = df["aov_mom_pct"].round(2)

        return df


if __name__ == "__main__":
    kpis = KPIService.get_executive_summary()
    print("Executive KPIs:", kpis)
    trends = KPIService.get_monthly_growth_trend()
    print("\nRecent Monthly Trends:")
    print(trends.tail(5)[["year_month", "total_delivered_revenue", "revenue_mom_pct", "delivered_orders"]])
