"""
Statistical Anomaly Detection Service for InsightIQ.

Uses Z-Score and Interquartile Range (IQR) methods to detect
revenue anomalies, sales spikes (e.g. Black Friday), and fulfillment drops.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.database import readonly_engine


class AnomalyDetector:
    """Detects statistical outliers and anomalies in business time series."""

    @staticmethod
    def detect_daily_revenue_anomalies(z_threshold: float = 2.5) -> pd.DataFrame:
        """
        Retrieves daily delivered revenue and applies both Z-score and IQR anomaly detection.
        """
        query = text(
            """
            SELECT
                d.full_date,
                d.year_month,
                COUNT(DISTINCT fo.order_id) AS order_count,
                ROUND(SUM(fo.total_order_amount), 2) AS daily_revenue
            FROM analytics.fact_orders fo
            JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
            WHERE fo.is_delivered = TRUE
            GROUP BY d.full_date, d.year_month
            ORDER BY d.full_date;
            """
        )
        with readonly_engine.connect() as conn:
            df = pd.read_sql(query, conn)

        if len(df) == 0:
            return df

        df["full_date"] = pd.to_datetime(df["full_date"])
        df["daily_revenue"] = df["daily_revenue"].astype(float)

        # 1. Rolling 7-day baseline
        df["rolling_mean_7d"] = df["daily_revenue"].rolling(window=7, min_periods=1).mean().round(2)
        df["rolling_std_7d"] = df["daily_revenue"].rolling(window=7, min_periods=1).std().fillna(1.0).round(2)

        # 2. Z-Score calculation
        mean_rev = df["daily_revenue"].mean()
        std_rev = df["daily_revenue"].std()
        df["z_score"] = ((df["daily_revenue"] - mean_rev) / std_rev).round(2)

        # 3. IQR calculation
        q1 = df["daily_revenue"].quantile(0.25)
        q3 = df["daily_revenue"].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        df["is_z_anomaly"] = df["z_score"].abs() > z_threshold
        df["is_iqr_anomaly"] = (df["daily_revenue"] < lower_bound) | (df["daily_revenue"] > upper_bound)
        df["is_anomaly"] = df["is_z_anomaly"] | df["is_iqr_anomaly"]

        # Classification of anomaly type
        conditions = [
            (df["is_anomaly"] & (df["daily_revenue"] > upper_bound)),
            (df["is_anomaly"] & (df["daily_revenue"] < lower_bound)),
        ]
        choices = ["Revenue Spike (Surge)", "Revenue Drop (Dip)"]
        df["anomaly_type"] = np.select(conditions, choices, default="Normal")

        return df

    @staticmethod
    def get_top_anomalies(top_n: int = 10) -> List[Dict[str, Any]]:
        """Returns the most extreme statistical anomalies with business context."""
        df = AnomalyDetector.detect_daily_revenue_anomalies()
        anomalies = df[df["is_anomaly"]].sort_values(by="z_score", key=abs, ascending=False).head(top_n)

        results = []
        for _, row in anomalies.iterrows():
            date_str = row["full_date"].strftime("%Y-%m-%d")
            # Contextual tagging for historical events
            context = "Unusual activity"
            if date_str == "2017-11-24":
                context = "Black Friday 2017 (Annual peak e-commerce sales event)"
            elif "2017-11" in date_str:
                context = "Black Friday promotional window surge"
            elif date_str.startswith("2016"):
                context = "Platform beta launch / limited operations phase"
            elif date_str >= "2018-09-01":
                context = "Dataset cutoff / phased cessation of order tracking"

            results.append(
                {
                    "date": date_str,
                    "daily_revenue": float(row["daily_revenue"]),
                    "order_count": int(row["order_count"]),
                    "z_score": float(row["z_score"]),
                    "anomaly_type": row["anomaly_type"],
                    "business_context": context,
                }
            )
        return results


if __name__ == "__main__":
    detector = AnomalyDetector()
    top = detector.get_top_anomalies(5)
    print("Top Statistical Anomalies in Olist History:")
    for a in top:
        print(f"  {a['date']}: R$ {a['daily_revenue']:,.2f} ({a['order_count']} orders) | Z={a['z_score']} | {a['business_context']}")
