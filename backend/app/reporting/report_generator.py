"""
Report Generation Service for InsightIQ.

Synthesizes structured business reports, executive summaries, operational audits,
and actionable investigation dossiers in Markdown and JSON export formats.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.app.services.kpi_service import KPIService
from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.customer_analytics import CustomerAnalyticsService

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Generates standardized executive business performance reports."""

    @staticmethod
    def generate_executive_business_report() -> Dict[str, Any]:
        """
        Compiles an end-to-end executive business performance report.
        Includes high-level metrics, growth trajectory, satisfaction health, and recommendations.
        """
        logger.info("Compiling Executive Business Report...")
        kpis = KPIService.get_executive_summary()
        corr = CorrelationAnalyzer.analyze_delivery_vs_satisfaction()
        anomalies = AnomalyDetector.get_top_anomalies(3)
        rfm = CustomerAnalyticsService.get_rfm_summary().head(5).to_dict(orient="records")

        report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown_report = f"""# 📈 InsightIQ Executive Business Performance Report
**Generated:** {report_timestamp}  
**Platform:** Brazilian E-Commerce Public Dataset (Olist)  
**Reporting Engine:** InsightIQ Autonomous BI Platform  

---

## 1. Executive Performance Summary
* **Total Delivered Revenue:** R$ {kpis['total_revenue']:,.2f}
* **Delivered GMV (Item Value):** R$ {kpis['total_gmv']:,.2f}
* **Delivered Freight Revenue:** R$ {kpis['total_freight']:,.2f}
* **Total Delivered Orders:** {kpis['delivered_orders']:,} of {kpis['total_orders']:,} total orders ({round(kpis['delivered_orders']/kpis['total_orders']*100, 1)}% fulfillment rate)
* **Average Order Value (AOV):** R$ {kpis['aov']:.2f}
* **Customer Base:** {kpis['unique_customers']:,} unique individuals (`customer_unique_id`)
* **Repeat Purchase Rate:** {kpis['repeat_purchase_rate_pct']}% ({kpis['repeat_customers']:,} repeat buyers)
* **Customer Satisfaction:** {kpis['avg_review_score']} ★ mean review score

---

## 2. Operational & Satisfaction Analysis
* **Delivery Lead Time:** Mean doorstep delivery requires **{kpis['avg_delivery_days']:.1f} days**.
* **On-Time Fulfillment Rate:** **{kpis['on_time_rate_pct']}%** of orders arrive on or ahead of estimated delivery.
* **Delay Impact on Satisfaction:**
  * **On-Time Cohort:** Mean score of **{corr['comparative_cohorts']['on_time_orders']['avg_review_score']} ★** ({corr['comparative_cohorts']['on_time_orders']['one_star_rate_pct']}% 1-star ratings).
  * **Delayed Cohort:** Plunges to **{corr['comparative_cohorts']['delayed_orders']['avg_review_score']} ★** with a **{corr['comparative_cohorts']['one_star_surge_factor']}x surge** in 1-star ratings ({corr['comparative_cohorts']['delayed_orders']['one_star_rate_pct']}%).
  * *Analytical Guardrail:* Statistical correlation ($r = {corr['correlations']['delay_vs_review']['pearson_r']}$) strongly links transit delays to dissatisfaction, but other variables (defects, seller communications) also co-occur.

---

## 3. Notable Historical Anomalies & Events
"""
        for a in anomalies:
            markdown_report += f"* **{a['date']}:** R$ {a['daily_revenue']:,.2f} ({a['order_count']:,} orders) — Z-Score: {a['z_score']:.2f} (*{a['business_context']}*)\n"

        markdown_report += f"""
---

## 4. Customer Segmentation Overview (Top RFM Segments)
"""
        for s in rfm:
            markdown_report += f"* **{s['customer_segment']}:** {s['customer_count']:,} customers ({s['pct_of_customers']}%) — Total Monetary Value: R$ {s['total_monetary_value']:,.2f} (Avg Order: R$ {s['avg_monetary_value']:.2f})\n"

        markdown_report += f"""
---

## 5. Strategic Recommendations & Next Investigations
1. **Logistics SLA Enforcement:** Standardize carrier agreements to enforce delivery notifications when transit extends beyond estimated dates, addressing the satisfaction cliff at > 3 days delay.
2. **Repeat Purchase Loyalty Programs:** With a 3.12% repeat purchase rate, implement automated post-purchase re-engagement sequences for high-frequency categories.
3. **Seller Operational Audits:** Establish threshold monitoring for merchants with cancellation rates > 5% to preserve marketplace trust.
"""

        return {
            "title": "Executive Business Performance Report",
            "timestamp": report_timestamp,
            "metrics": kpis,
            "markdown": markdown_report,
            "sections": [
                "Executive Performance Summary",
                "Operational & Satisfaction Analysis",
                "Notable Historical Anomalies",
                "Customer Segmentation Overview",
                "Strategic Recommendations",
            ],
        }
