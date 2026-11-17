"""
Operational and Fulfillment Bottleneck Investigation Service for InsightIQ.

Identifies problematic sellers with high cancellation rates, underperforming logistics routes,
and transit bottlenecks using PostgreSQL dimensional analytics.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import text

from backend.app.services.database import readonly_engine

logger = logging.getLogger(__name__)


class OperationalBottleneckInvestigator:
    """Investigates operational friction across sellers and logistics routes."""

    @staticmethod
    def investigate_problematic_sellers(min_orders: int = 20, top_n: int = 10) -> Dict[str, Any]:
        """
        Identifies sellers with abnormally high cancellation rates and low satisfaction ratings.
        """
        query = text(
            """
            SELECT
                seller_id,
                seller_city,
                seller_state,
                total_orders,
                cancellation_rate_pct,
                total_sales_value,
                avg_review_score
            FROM analytics.v_seller_performance
            WHERE total_orders >= :min_orders
            ORDER BY cancellation_rate_pct DESC, avg_review_score ASC
            LIMIT :limit;
            """
        )

        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"min_orders": min_orders, "limit": top_n})

        records = df.to_dict(orient="records")
        high_cancel_sellers = [r for r in records if r["cancellation_rate_pct"] > 5.0]

        summary = (
            f"Screened sellers with >= {min_orders} orders. "
            f"Identified {len(records)} high-risk sellers. "
            f"Worst seller cancellation rate: {records[0]['cancellation_rate_pct']}% "
            f"(Seller ID: {records[0]['seller_id'][:8]}... in {records[0]['seller_state']}) "
            f"with an average review score of {records[0]['avg_review_score']} ★."
        ) if records else "No sellers flagged under the specified threshold."

        return {
            "min_orders_threshold": min_orders,
            "problematic_sellers_count": len(records),
            "sellers": records,
            "executive_summary": summary,
        }

    @staticmethod
    def investigate_transit_bottlenecks(min_orders: int = 50, top_n: int = 10) -> Dict[str, Any]:
        """
        Identifies inter-state shipping corridors with the longest delivery lead times and lowest on-time rates.
        """
        query = text(
            """
            SELECT
                ds.seller_state,
                dc.customer_state,
                COUNT(DISTINCT fo.order_id) AS total_orders,
                ROUND(AVG(fo.delivery_lead_time_days), 1) AS avg_lead_time_days,
                ROUND(AVG(fo.delivery_delay_days), 1) AS avg_delay_days,
                ROUND(COUNT(CASE WHEN fo.is_on_time = TRUE THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100.0, 1) AS on_time_rate_pct,
                ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score
            FROM analytics.fact_orders fo
            JOIN analytics.fact_order_items foi ON fo.order_id = foi.order_id
            JOIN analytics.dim_sellers ds ON foi.seller_id = ds.seller_id
            JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
            WHERE fo.is_delivered = TRUE 
              AND fo.delivery_lead_time_days IS NOT NULL
            GROUP BY ds.seller_state, dc.customer_state
            HAVING COUNT(DISTINCT fo.order_id) >= :min_orders
            ORDER BY avg_lead_time_days DESC
            LIMIT :limit;
            """
        )

        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"min_orders": min_orders, "limit": top_n})

        records = df.to_dict(orient="records")
        worst_route = records[0] if records else None

        summary = (
            f"Screened inter-state corridors with >= {min_orders} orders. "
            f"Longest transit corridor: {worst_route['seller_state']} -> {worst_route['customer_state']} "
            f"with an average lead time of {worst_route['avg_lead_time_days']} days "
            f"(On-time rate: {worst_route['on_time_rate_pct']}%, Avg Rating: {worst_route['avg_review_score']} ★)."
        ) if worst_route else "No routes identified."

        return {
            "min_orders_threshold": min_orders,
            "corridors": records,
            "executive_summary": summary,
        }

