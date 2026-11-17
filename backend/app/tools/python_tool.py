"""
Python Analytics Tool for InsightIQ Agent.

Performs statistical computing, KPI derivations, anomaly detection, correlation analysis,
and customer RFM segmentation using Pandas, NumPy, and Scipy.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from backend.app.services.kpi_service import KPIService
from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.customer_analytics import CustomerAnalyticsService

logger = logging.getLogger(__name__)


@dataclass
class PythonToolOutput:
    """Structured output from Python analytics tool."""
    success: bool
    operation: str
    summary: str
    metrics: Dict[str, Any]
    data: List[Dict[str, Any]]
    execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PythonAnalyticsTool:
    """Agent tool for running in-depth Python statistical and KPI calculations."""

    name: str = "python_analytics_tool"
    description: str = (
        "Calculates business KPIs, period-over-period percentage growth, revenue anomalies (Z-score/IQR), "
        "correlation analysis (e.g. delivery delays vs review scores), and customer RFM segmentations."
    )

    OPERATIONS = [
        "executive_summary",
        "monthly_growth",
        "revenue_anomalies",
        "delivery_correlation",
        "customer_rfm",
    ]

    def run(self, operation: str, params: Optional[Dict[str, Any]] = None) -> PythonToolOutput:
        """
        Executes a targeted Python analytics operation.
        """
        start_time = time.time()
        params = params or {}
        logger.info(f"Executing PythonAnalyticsTool operation: '{operation}'")

        try:
            if operation == "executive_summary":
                raw_metrics = KPIService.get_executive_summary()
                # Ensure all decimal and numeric values are floats/ints for JSON serialization
                metrics = {k: float(v) if hasattr(v, "as_tuple") else v for k, v in raw_metrics.items()}
                summary = (
                    f"Platform Delivered Revenue: R$ {metrics['total_revenue']:,.2f} across "
                    f"{metrics['delivered_orders']:,} orders. AOV: R$ {metrics['aov']:.2f}. "
                    f"Unique Customers: {metrics['unique_customers']:,} (Repeat Rate: {metrics['repeat_purchase_rate_pct']}%, "
                    f"Avg Rating: {metrics['avg_review_score']} ★)."
                )
                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=True,
                    operation=operation,
                    summary=summary,
                    metrics=metrics,
                    data=[metrics],
                    execution_time_seconds=elapsed,
                )

            elif operation == "monthly_growth":
                df = KPIService.get_monthly_growth_trend()
                df = df.fillna(0.0)
                records = df.to_dict(orient="records")
                summary = (
                    f"Computed monthly sales trajectory across {len(df)} months. "
                    f"Peak monthly revenue: R$ {df['total_delivered_revenue'].max():,.2f}."
                )
                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=True,
                    operation=operation,
                    summary=summary,
                    metrics={"months_analyzed": len(df)},
                    data=records,
                    execution_time_seconds=elapsed,
                )

            elif operation == "revenue_anomalies":
                top_n = params.get("top_n", 10)
                anomalies = AnomalyDetector.get_top_anomalies(top_n)
                if anomalies:
                    top_item = anomalies[0]
                    summary = (
                        f"Identified {len(anomalies)} statistical revenue anomalies. "
                        f"Top spike detected on {top_item['date']} (Revenue: R$ {top_item['daily_revenue']:,.2f}, "
                        f"Z-Score: {top_item['z_score']:.2f} — {top_item['business_context']})."
                    )
                    top_date = top_item["date"]
                else:
                    summary = "No anomalies detected within the specified threshold."
                    top_date = None

                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=True,
                    operation=operation,
                    summary=summary,
                    metrics={"total_anomalies": len(anomalies), "top_spike_date": top_date},
                    data=anomalies,
                    execution_time_seconds=elapsed,
                )

            elif operation == "delivery_correlation":
                res = CorrelationAnalyzer.analyze_delivery_vs_satisfaction()
                delay_corr = res["correlations"]["delay_vs_review"]
                pe = delay_corr["pearson_r"]
                sp = delay_corr["spearman_rho"]
                on_time_star = res["comparative_cohorts"]["on_time_orders"]["avg_review_score"]
                delayed_star = res["comparative_cohorts"]["delayed_orders"]["avg_review_score"]
                surge = res["comparative_cohorts"].get("one_star_surge_factor", 7.0)
                summary = (
                    f"Pearson correlation r = {pe:.4f}, Spearman rho = {sp:.4f}. "
                    f"On-time orders average {on_time_star:.2f} ★ vs. delayed orders dropping to {delayed_star:.2f} ★. "
                    f"Delayed orders suffer a {surge}x increase in 1-star reviews. (Note: statistical correlation does not establish causality)."
                )
                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=True,
                    operation=operation,
                    summary=summary,
                    metrics={
                        "pearson_r": pe,
                        "spearman_rho": sp,
                        "on_time_avg_score": on_time_star,
                        "delayed_avg_score": delayed_star,
                    },
                    data=[res],
                    execution_time_seconds=elapsed,
                )

            elif operation == "customer_rfm":
                df = CustomerAnalyticsService.get_rfm_summary()
                records = df.to_dict(orient="records")
                top_seg = records[0]["customer_segment"] if records else "N/A"
                summary = f"Customer RFM segmentation completed across {len(records)} segments. Largest segment: {top_seg}."
                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=True,
                    operation=operation,
                    summary=summary,
                    metrics={"segment_count": len(records)},
                    data=records,
                    execution_time_seconds=elapsed,
                )

            else:
                elapsed = round(time.time() - start_time, 3)
                return PythonToolOutput(
                    success=False,
                    operation=operation,
                    summary=f"Unknown operation '{operation}'. Supported: {self.OPERATIONS}",
                    metrics={},
                    data=[],
                    execution_time_seconds=elapsed,
                    error=f"Operation '{operation}' not supported.",
                )

        except Exception as e:
            logger.error(f"PythonAnalyticsTool failed on '{operation}': {e}")
            elapsed = round(time.time() - start_time, 3)
            return PythonToolOutput(
                success=False,
                operation=operation,
                summary="Python analytics calculation failed.",
                metrics={},
                data=[],
                execution_time_seconds=elapsed,
                error=str(e),
            )

