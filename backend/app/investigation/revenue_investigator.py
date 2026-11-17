"""
Revenue Anomaly and Period Change Investigation Service for InsightIQ.

Decomposes revenue expansions and contractions into order volume effects, average order value (AOV) effects,
and category/regional drivers using SQL analytics and variance decomposition.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import text

from backend.app.services.database import readonly_engine

logger = logging.getLogger(__name__)


class RevenueAnomalyInvestigator:
    """Investigates revenue fluctuations, period-over-period changes, and anomalous spikes."""

    @staticmethod
    def investigate_period_change(current_month: str, prior_month: str) -> Dict[str, Any]:
        """
        Decomposes month-over-month revenue changes between two periods (YYYY-MM).
        Applies volume-price variance decomposition and identifies category/state drivers.
        """
        query_totals = text(
            """
            SELECT
                year_month,
                delivered_orders,
                total_delivered_revenue,
                aov
            FROM analytics.v_monthly_sales
            WHERE year_month IN (:prior, :curr)
            ORDER BY year_month;
            """
        )

        with readonly_engine.connect() as conn:
            df_totals = pd.read_sql(query_totals, conn, params={"prior": prior_month, "curr": current_month})

        if len(df_totals) < 2:
            return {
                "error": f"Insufficient data for periods '{prior_month}' and '{current_month}'.",
                "current_month": current_month,
                "prior_month": prior_month,
            }

        prior_data = df_totals[df_totals["year_month"] == prior_month].iloc[0]
        curr_data = df_totals[df_totals["year_month"] == current_month].iloc[0]

        r_prior = float(prior_data["total_delivered_revenue"])
        r_curr = float(curr_data["total_delivered_revenue"])
        o_prior = int(prior_data["delivered_orders"])
        o_curr = int(curr_data["delivered_orders"])
        aov_prior = float(prior_data["aov"])
        aov_curr = float(curr_data["aov"])

        delta_revenue = r_curr - r_prior
        pct_change = round((delta_revenue / r_prior) * 100.0, 2) if r_prior > 0 else 0.0

        # Variance Decomposition:
        # Delta Revenue = Volume Effect + Price/AOV Effect
        volume_effect = (o_curr - o_prior) * aov_prior
        price_effect = (aov_curr - aov_prior) * o_curr

        # Category level drivers
        query_categories = text(
            """
            WITH curr_cat AS (
                SELECT
                    COALESCE(dp.product_category_name_english, 'unknown') AS category,
                    SUM(foi.price + foi.freight_value) AS curr_rev
                FROM analytics.fact_order_items foi
                JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
                JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
                LEFT JOIN analytics.dim_products dp ON foi.product_id = dp.product_id
                WHERE fo.is_delivered = TRUE AND d.year_month = :curr
                GROUP BY 1
            ),
            prior_cat AS (
                SELECT
                    COALESCE(dp.product_category_name_english, 'unknown') AS category,
                    SUM(foi.price + foi.freight_value) AS prior_rev
                FROM analytics.fact_order_items foi
                JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
                JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
                LEFT JOIN analytics.dim_products dp ON foi.product_id = dp.product_id
                WHERE fo.is_delivered = TRUE AND d.year_month = :prior
                GROUP BY 1
            )
            SELECT
                COALESCE(c.category, p.category) AS category,
                COALESCE(p.prior_rev, 0) AS prior_revenue,
                COALESCE(c.curr_rev, 0) AS current_revenue,
                ROUND((COALESCE(c.curr_rev, 0) - COALESCE(p.prior_rev, 0))::NUMERIC, 2) AS delta_revenue
            FROM curr_cat c
            FULL OUTER JOIN prior_cat p ON c.category = p.category
            ORDER BY delta_revenue DESC;
            """
        )

        with readonly_engine.connect() as conn:
            df_cat = pd.read_sql(query_categories, conn, params={"prior": prior_month, "curr": current_month})

        top_growth_categories = df_cat.head(3).to_dict(orient="records")
        top_drag_categories = df_cat.tail(3).sort_values(by="delta_revenue", ascending=True).to_dict(orient="records")

        # Regional State drivers
        query_states = text(
            """
            WITH curr_st AS (
                SELECT
                    dc.customer_state,
                    SUM(fo.total_order_amount) AS curr_rev
                FROM analytics.fact_orders fo
                JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
                JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
                WHERE fo.is_delivered = TRUE AND d.year_month = :curr
                GROUP BY 1
            ),
            prior_st AS (
                SELECT
                    dc.customer_state,
                    SUM(fo.total_order_amount) AS prior_rev
                FROM analytics.fact_orders fo
                JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
                JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
                WHERE fo.is_delivered = TRUE AND d.year_month = :prior
                GROUP BY 1
            )
            SELECT
                COALESCE(c.customer_state, p.customer_state) AS customer_state,
                COALESCE(p.prior_rev, 0) AS prior_revenue,
                COALESCE(c.curr_rev, 0) AS current_revenue,
                ROUND((COALESCE(c.curr_rev, 0) - COALESCE(p.prior_rev, 0))::NUMERIC, 2) AS delta_revenue
            FROM curr_st c
            FULL OUTER JOIN prior_st p ON c.customer_state = p.customer_state
            ORDER BY delta_revenue DESC;
            """
        )

        with readonly_engine.connect() as conn:
            df_st = pd.read_sql(query_states, conn, params={"prior": prior_month, "curr": current_month})

        top_growth_states = df_st.head(3).to_dict(orient="records")
        top_drag_states = df_st.tail(3).sort_values(by="delta_revenue", ascending=True).to_dict(orient="records")

        direction = "expansion" if delta_revenue >= 0 else "contraction"
        primary_driver = "order volume" if abs(volume_effect) > abs(price_effect) else "average spend per order (AOV)"

        executive_takeaway = (
            f"Revenue underwent a {direction} of R$ {abs(delta_revenue):,.2f} ({pct_change:+,.2f}%) "
            f"from {prior_month} to {current_month}. The change was primarily driven by {primary_driver} "
            f"(Volume Effect: R$ {volume_effect:+,.2f}, Price/AOV Effect: R$ {price_effect:+,.2f})."
        )

        return {
            "prior_period": prior_month,
            "current_period": current_month,
            "prior_revenue": r_prior,
            "current_revenue": r_curr,
            "delta_revenue": round(delta_revenue, 2),
            "pct_change": pct_change,
            "volume_effect": round(volume_effect, 2),
            "price_effect": round(price_effect, 2),
            "primary_driver": primary_driver,
            "top_growth_categories": top_growth_categories,
            "top_drag_categories": top_drag_categories,
            "top_growth_states": top_growth_states,
            "top_drag_states": top_drag_states,
            "executive_takeaway": executive_takeaway,
        }

    @staticmethod
    def investigate_date_anomaly(date_str: str = "2017-11-24") -> Dict[str, Any]:
        """
        Deep-dive investigation of a specific anomalous date spike (e.g., Black Friday 2017).
        """
        query_date = text(
            """
            SELECT
                d.full_date,
                COUNT(DISTINCT fo.order_id) AS orders_count,
                ROUND(SUM(fo.total_order_amount), 2) AS daily_revenue,
                ROUND(AVG(fo.total_order_amount), 2) AS daily_aov
            FROM analytics.fact_orders fo
            JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
            WHERE fo.is_delivered = TRUE AND d.full_date = :dt
            GROUP BY d.full_date;
            """
        )

        # Baseline 30 days prior
        query_baseline = text(
            """
            SELECT
                ROUND(AVG(daily_rev), 2) AS baseline_daily_revenue,
                ROUND(AVG(daily_orders), 1) AS baseline_daily_orders
            FROM (
                SELECT
                    d.full_date,
                    SUM(fo.total_order_amount) AS daily_rev,
                    COUNT(DISTINCT fo.order_id) AS daily_orders
                FROM analytics.fact_orders fo
                JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
                WHERE fo.is_delivered = TRUE
                  AND d.full_date >= (:dt::date - INTERVAL '30 days')
                  AND d.full_date < :dt::date
                GROUP BY d.full_date
            ) sub;
            """
        )

        with readonly_engine.connect() as conn:
            df_target = pd.read_sql(query_date, conn, params={"dt": date_str})
            df_base = pd.read_sql(query_baseline, conn, params={"dt": date_str})

        if len(df_target) == 0:
            return {"error": f"No delivered orders found on date {date_str}."}

        target = df_target.iloc[0]
        base = df_base.iloc[0]

        rev = float(target["daily_revenue"])
        orders = int(target["orders_count"])
        base_rev = float(base["baseline_daily_revenue"]) if pd.notna(base["baseline_daily_revenue"]) else 1.0
        base_orders = float(base["baseline_daily_orders"]) if pd.notna(base["baseline_daily_orders"]) else 1.0

        surge_revenue_factor = round(rev / base_rev, 2)
        surge_order_factor = round(orders / base_orders, 2)

        return {
            "date": date_str,
            "daily_revenue": rev,
            "orders_count": orders,
            "daily_aov": float(target["daily_aov"]),
            "baseline_daily_revenue": base_rev,
            "baseline_daily_orders": base_orders,
            "revenue_surge_multiplier": surge_revenue_factor,
            "order_surge_multiplier": surge_order_factor,
            "executive_summary": (
                f"On {date_str}, delivered revenue reached R$ {rev:,.2f} across {orders:,} orders. "
                f"This represented a {surge_revenue_factor}x revenue surge and a {surge_order_factor}x order surge "
                f"compared to the preceding 30-day baseline (mean daily revenue: R$ {base_rev:,.2f})."
            ),
        }
