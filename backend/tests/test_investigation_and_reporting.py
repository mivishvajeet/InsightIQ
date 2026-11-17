"""
Comprehensive Test Suite for InsightIQ Business Investigation and Reporting.

Tests:
1. Revenue change variance decomposition (Volume Effect vs Price Effect)
2. Black Friday date spike anomaly investigation
3. Customer satisfaction drivers and delay threshold cliff
4. Problematic sellers screening (cancellation rates and ratings)
5. Inter-state transit corridor bottlenecks
6. Underperforming category identification (satisfaction and freight burden)
7. BusinessInvestigationTool unified execution
8. ReportGeneratorService and ReportGenerationTool Markdown/JSON synthesis
9. End-to-end OrchestratorAgent execution for investigation and report intents
"""

import pytest
from backend.app.investigation.revenue_investigator import RevenueAnomalyInvestigator
from backend.app.investigation.satisfaction_investigator import SatisfactionDriverInvestigator
from backend.app.investigation.operational_investigator import OperationalBottleneckInvestigator
from backend.app.investigation.category_investigator import CategoryPerformanceInvestigator
from backend.app.investigation.investigation_tool import BusinessInvestigationTool
from backend.app.reporting.report_generator import ReportGeneratorService
from backend.app.reporting.report_tool import ReportGenerationTool
from backend.app.agents.orchestrator import orchestrator_agent


def test_revenue_period_variance_decomposition():
    """Verify month-over-month volume vs price decomposition."""
    res = RevenueAnomalyInvestigator.investigate_period_change("2018-04", "2018-03")
    assert "delta_revenue" in res
    assert "volume_effect" in res
    assert "price_effect" in res
    assert "primary_driver" in res
    assert len(res["top_growth_categories"]) > 0
    assert len(res["top_drag_categories"]) > 0
    assert "executive_takeaway" in res


def test_revenue_date_anomaly_investigation():
    """Verify Black Friday 2017 date surge multiplier against 30-day baseline."""
    res = RevenueAnomalyInvestigator.investigate_date_anomaly("2017-11-24")
    assert res["date"] == "2017-11-24"
    assert res["daily_revenue"] > 100000.0
    assert res["orders_count"] > 1000
    assert res["revenue_surge_multiplier"] > 3.0
    assert "Black Friday" in res["executive_summary"] or "surge" in res["executive_summary"]


def test_satisfaction_driver_investigation():
    """Verify satisfaction drivers, delay tiers, and causation guardrails."""
    res = SatisfactionDriverInvestigator.investigate_satisfaction_drivers()
    assert res["pearson_r"] < -0.20
    assert len(res["delay_tiers"]) >= 4
    assert "causation_guardrail" in res
    assert "correlation does not prove" in res["causation_guardrail"].lower()


def test_problematic_sellers_investigation():
    """Verify detection of sellers with high cancellation rates."""
    res = OperationalBottleneckInvestigator.investigate_problematic_sellers(min_orders=15, top_n=5)
    assert res["problematic_sellers_count"] > 0
    top_seller = res["sellers"][0]
    assert "seller_id" in top_seller
    assert "cancellation_rate_pct" in top_seller


def test_transit_corridors_investigation():
    """Verify identification of high-latency inter-state logistics corridors."""
    res = OperationalBottleneckInvestigator.investigate_transit_bottlenecks(min_orders=30, top_n=5)
    assert len(res["corridors"]) > 0
    worst = res["corridors"][0]
    assert "seller_state" in worst
    assert "customer_state" in worst
    assert worst["avg_lead_time_days"] > 10.0


def test_underperforming_categories_investigation():
    """Verify screening for product categories with low reviews or freight burden."""
    res = CategoryPerformanceInvestigator.investigate_underperforming_categories(min_items_sold=30, top_n=5)
    assert len(res["underperforming_categories"]) > 0
    worst = res["underperforming_categories"][0]
    assert "category" in worst
    assert "avg_review_score" in worst
    assert worst["avg_review_score"] < 4.5


def test_business_investigation_tool_dispatch():
    """Verify unified BusinessInvestigationTool executes across multiple investigation types."""
    tool = BusinessInvestigationTool()

    out_rev = tool.run("revenue_anomaly", {"current_month": "2018-05", "prior_month": "2018-04"})
    assert out_rev.success is True
    assert "delta_revenue" in out_rev.metrics

    out_sat = tool.run("satisfaction_drivers")
    assert out_sat.success is True
    assert "pearson_r" in out_sat.metrics
    assert "causation" in out_sat.causation_guardrail.lower()

    out_sel = tool.run("seller_performance")
    assert out_sel.success is True
    assert len(out_sel.evidence_data) > 0


def test_report_generator_and_tool():
    """Verify executive business performance report generation and Markdown compilation."""
    service = ReportGeneratorService()
    report = service.generate_executive_business_report()

    assert report["title"] == "Executive Business Performance Report"
    assert "Total Delivered Revenue" in report["markdown"]
    assert "Operational & Satisfaction Analysis" in report["markdown"]
    assert len(report["sections"]) >= 4

    tool = ReportGenerationTool(service=service)
    tool_out = tool.run()
    assert tool_out.success is True
    assert len(tool_out.markdown_content) > 200


def test_orchestrator_investigation_and_report_workflows():
    """Verify OrchestratorAgent routes and executes investigation and report queries."""
    # 1. Investigation workflow
    res_inv = orchestrator_agent.run("Why did revenue decline in a particular period?")
    assert res_inv.intent == "investigation"
    assert "business_investigation_tool" in res_inv.tools_used
    assert len(res_inv.execution_steps) >= 3

    # 2. Report workflow
    res_rep = orchestrator_agent.run("Generate business performance report")
    assert res_rep.intent == "report"
    assert "report_generation_tool" in res_rep.tools_used
    assert "# 📈 InsightIQ Executive Business Performance Report" in res_rep.final_answer

