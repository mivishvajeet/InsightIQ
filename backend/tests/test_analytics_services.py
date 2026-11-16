"""
Phase 4 Python Analytics Services Unit & Integration Test Suite.

Verifies:
1. KPIService executive summary and MoM growth metrics.
2. AnomalyDetector statistical outlier detection on daily revenue.
3. CorrelationAnalyzer statistical associations (delay vs satisfaction).
4. CustomerAnalyticsService RFM segmentation and cohort retention.
"""

import pytest
import pandas as pd
from backend.app.services.kpi_service import KPIService
from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.customer_analytics import CustomerAnalyticsService


def test_kpi_service_executive_summary():
    """Verify executive headline KPIs match Phase 1 & Phase 3 ground truth."""
    kpis = KPIService.get_executive_summary()
    assert float(kpis["total_revenue"]) == 15424463.65
    assert float(kpis["total_gmv"]) == 13221498.11
    assert float(kpis["aov"]) == 159.88
    assert kpis["total_orders"] == 99441
    assert kpis["delivered_orders"] == 96478
    assert kpis["unique_customers"] == 96096
    assert kpis["repeat_customers"] == 2997
    assert float(kpis["repeat_purchase_rate_pct"]) == 3.12
    assert float(kpis["avg_review_score"]) == 4.09


def test_kpi_service_monthly_growth():
    """Verify monthly growth dataframe structure and calculations."""
    df = KPIService.get_monthly_growth_trend()
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 20
    assert "revenue_mom_pct" in df.columns
    assert "orders_mom_pct" in df.columns
    # Check that highest revenue month is November 2017 (Black Friday)
    max_month = df.loc[df["total_delivered_revenue"].idxmax()]
    assert max_month["year_month"] == "2017-11"


def test_anomaly_detector_detects_black_friday():
    """Verify AnomalyDetector identifies 2017-11-24 (Black Friday) as extreme anomaly."""
    df = AnomalyDetector.detect_daily_revenue_anomalies(z_threshold=2.5)
    assert isinstance(df, pd.DataFrame)
    assert "z_score" in df.columns
    assert "is_anomaly" in df.columns

    bf_row = df[df["full_date"] == "2017-11-24"]
    assert len(bf_row) == 1
    assert bf_row["is_anomaly"].values[0] == True
    assert bf_row["z_score"].values[0] > 5.0
    assert bf_row["anomaly_type"].values[0] == "Revenue Spike (Surge)"


def test_correlation_delay_vs_review_score():
    """Verify negative correlation between delivery delay and review satisfaction."""
    res = CorrelationAnalyzer.analyze_delivery_vs_satisfaction()
    corr = res["correlations"]["delay_vs_review"]
    assert corr["pearson_r"] < -0.20, f"Expected negative correlation, got {corr['pearson_r']}"
    assert corr["spearman_rho"] < -0.15

    cohorts = res["comparative_cohorts"]
    assert cohorts["on_time_orders"]["avg_review_score"] > cohorts["delayed_orders"]["avg_review_score"]
    assert cohorts["on_time_orders"]["avg_review_score"] > 4.0
    assert cohorts["delayed_orders"]["avg_review_score"] < 3.0
    assert cohorts["one_star_surge_factor"] > 4.0


def test_customer_rfm_summary_completeness():
    """Verify customer RFM segments sum to exactly 96,096 unique customers."""
    df = CustomerAnalyticsService.get_rfm_summary()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6
    expected_segments = {
        "Hibernating / One-Offs",
        "Recent One-Offs",
        "High-Value Recent",
        "At Risk Repeaters",
        "Loyal Customers",
        "Champions",
    }
    actual_segments = set(df["customer_segment"])
    assert actual_segments == expected_segments
    assert df["customer_count"].sum() == 96096
