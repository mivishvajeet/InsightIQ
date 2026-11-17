"""
Product Category Performance and Underperformance Investigator for InsightIQ.

Identifies problematic merchandise categories suffering from substandard customer ratings,
disproportionate freight costs, or declining revenue trends.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import text

from backend.app.services.database import readonly_engine

logger = logging.getLogger(__name__)


class CategoryPerformanceInvestigator:
    """Investigates product category health, margins, and customer satisfaction drags."""

    @staticmethod
    def investigate_underperforming_categories(min_items_sold: int = 50, top_n: int = 10) -> Dict[str, Any]:
        """
        Identifies categories with lowest customer satisfaction ratings and highest freight cost burden.
        """
        query = text(
            """
            SELECT
                COALESCE(dp.product_category_name_english, 'unknown') AS category,
                COUNT(DISTINCT fo.order_id) AS total_orders,
                COUNT(foi.order_item_id) AS total_items_sold,
                ROUND(SUM(foi.price), 2) AS total_item_revenue,
                ROUND(SUM(foi.freight_value), 2) AS total_freight_revenue,
                ROUND(AVG(foi.price), 2) AS avg_item_price,
                ROUND((SUM(foi.freight_value) / NULLIF(SUM(foi.price), 0) * 100.0), 1) AS freight_to_price_pct,
                ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score,
                ROUND(COUNT(CASE WHEN fo.latest_review_score = 1 THEN 1 END)::NUMERIC / COUNT(fo.latest_review_score)::NUMERIC * 100.0, 1) AS one_star_pct
            FROM analytics.fact_order_items foi
            JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
            LEFT JOIN analytics.dim_products dp ON foi.product_id = dp.product_id
            WHERE fo.is_delivered = TRUE
            GROUP BY 1
            HAVING COUNT(foi.order_item_id) >= :min_items
            ORDER BY avg_review_score ASC, freight_to_price_pct DESC
            LIMIT :limit;
            """
        )

        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"min_items": min_items_sold, "limit": top_n})

        records = df.to_dict(orient="records")
        worst = records[0] if records else None

        summary = (
            f"Screened categories with >= {min_items_sold} items sold. "
            f"Lowest satisfaction category is '{worst['category']}' with {worst['avg_review_score']} ★ "
            f"({worst['one_star_pct']}% 1-star ratings across {worst['total_orders']:,} orders). "
            f"Freight cost burden for this category represents {worst['freight_to_price_pct']}% of item price."
        ) if worst else "No categories found."

        return {
            "min_items_threshold": min_items_sold,
            "underperforming_categories": records,
            "executive_summary": summary,
        }
