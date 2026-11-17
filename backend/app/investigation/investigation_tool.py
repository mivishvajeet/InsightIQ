"""
Business Investigation Tool for InsightIQ Agent.

Executes structured deep-dive investigations:
1. Revenue change variance decomposition (Volume vs AOV)
2. Customer satisfaction degradation and delay thresholds
3. Seller operational health and cancellation risks
4. Logistics transit bottlenecks
5. Underperforming merchandise categories
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from backend.app.investigation.revenue_investigator import RevenueAnomalyInvestigator
from backend.app.investigation.satisfaction_investigator import SatisfactionDriverInvestigator
from backend.app.investigation.operational_investigator import OperationalBottleneckInvestigator
from backend.app.investigation.category_investigator import CategoryPerformanceInvestigator

logger = logging.getLogger(__name__)


@dataclass
class InvestigationToolOutput:
    """Structured output from business investigation tool."""
    success: bool
    investigation_type: str
    executive_summary: str
    metrics: Dict[str, Any]
    evidence_data: List[Dict[str, Any]]
    causation_guardrail: str
    recommended_action: str
    execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BusinessInvestigationTool:
    """Agent tool for running multi-step root cause analysis and operational investigations."""

    name: str = "business_investigation_tool"
    description: str = (
        "Investigates revenue fluctuations (variance decomposition), declining customer satisfaction "
        "(delay threshold cliffs), high-cancellation sellers, transit corridor bottlenecks, and "
        "underperforming product categories with strict correlation vs causation guardrails."
    )

    INVESTIGATION_TYPES = [
        "revenue_anomaly",
        "satisfaction_drivers",
        "seller_performance",
        "transit_bottlenecks",
        "underperforming_categories",
    ]

    def run(self, investigation_type: str, params: Optional[Dict[str, Any]] = None) -> InvestigationToolOutput:
        """
        Executes a targeted business investigation workflow.
        """
        start_time = time.time()
        params = params or {}
        logger.info(f"Executing BusinessInvestigationTool: '{investigation_type}' with params {params}")

        try:
            if investigation_type == "revenue_anomaly":
                if "date" in params:
                    res = RevenueAnomalyInvestigator.investigate_date_anomaly(params["date"])
                    evidence = [res]
                    metrics = {
                        "date": res.get("date"),
                        "daily_revenue": res.get("daily_revenue"),
                        "revenue_surge_multiplier": res.get("revenue_surge_multiplier"),
                    }
                    summary = res.get("executive_summary", "")
                    rec = "Ensure server capacity, inventory buffers, and logistics SLAs are pre-booked 60 days before the annual promotional surge."
                else:
                    curr = params.get("current_month", "2018-04")
                    prior = params.get("prior_month", "2018-03")
                    res = RevenueAnomalyInvestigator.investigate_period_change(curr, prior)
                    evidence = res.get("top_growth_categories", []) + res.get("top_drag_categories", [])
                    metrics = {
                        "delta_revenue": res.get("delta_revenue"),
                        "pct_change": res.get("pct_change"),
                        "volume_effect": res.get("volume_effect"),
                        "price_effect": res.get("price_effect"),
                        "primary_driver": res.get("primary_driver"),
                    }
                    summary = res.get("executive_takeaway", "")
                    rec = f"Focus marketing campaigns on reversing volume drop in dragging categories such as {res.get('top_drag_categories', [{}])[0].get('category', 'core lines')}."

                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=True,
                    investigation_type=investigation_type,
                    executive_summary=summary,
                    metrics=metrics,
                    evidence_data=evidence,
                    causation_guardrail="Demand fluctuations reflect seasonal and category-specific volume shifts; marketing promotions should be decoupled from baseline organic growth.",
                    recommended_action=rec,
                    execution_time_seconds=elapsed,
                )

            elif investigation_type == "satisfaction_drivers":
                res = SatisfactionDriverInvestigator.investigate_satisfaction_drivers()
                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=True,
                    investigation_type=investigation_type,
                    executive_summary=res["executive_summary"],
                    metrics={
                        "pearson_r": res["pearson_r"],
                        "on_time_avg_score": res["comparative_cohorts"]["on_time_orders"]["avg_review_score"],
                        "delayed_avg_score": res["comparative_cohorts"]["delayed_orders"]["avg_review_score"],
                        "one_star_surge_factor": res["comparative_cohorts"]["one_star_surge_factor"],
                    },
                    evidence_data=res["delay_tiers"],
                    causation_guardrail=res["causation_guardrail"],
                    recommended_action="Implement proactive delivery delay notification alerts and seller penalty SLAs when carrier transit exceeds estimated date by > 48 hours.",
                    execution_time_seconds=elapsed,
                )

            elif investigation_type == "seller_performance":
                min_o = params.get("min_orders", 20)
                limit = params.get("top_n", 10)
                res = OperationalBottleneckInvestigator.investigate_problematic_sellers(min_orders=min_o, top_n=limit)
                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=True,
                    investigation_type=investigation_type,
                    executive_summary=res["executive_summary"],
                    metrics={"flagged_sellers": res["problematic_sellers_count"]},
                    evidence_data=res["sellers"],
                    causation_guardrail="Sellers with high cancellation rates may suffer from inventory stockouts or pricing sync errors rather than deliberate bad faith.",
                    recommended_action="Initiate formal seller audit for merchants exhibiting > 5% cancellation rates and review suspension policies for repeated stockout cancellations.",
                    execution_time_seconds=elapsed,
                )

            elif investigation_type == "transit_bottlenecks":
                min_o = params.get("min_orders", 50)
                limit = params.get("top_n", 10)
                res = OperationalBottleneckInvestigator.investigate_transit_bottlenecks(min_orders=min_o, top_n=limit)
                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=True,
                    investigation_type=investigation_type,
                    executive_summary=res["executive_summary"],
                    metrics={"analyzed_routes": len(res["corridors"])},
                    evidence_data=res["corridors"],
                    causation_guardrail="Inter-state transit delays correlate with regional geography and carrier hubs in North/Northeast Brazil.",
                    recommended_action="Partner with regional logistics 3PL providers in high-friction states to optimize fulfillment hubs and lower average transit lead times.",
                    execution_time_seconds=elapsed,
                )

            elif investigation_type == "underperforming_categories":
                min_i = params.get("min_items_sold", 50)
                limit = params.get("top_n", 10)
                res = CategoryPerformanceInvestigator.investigate_underperforming_categories(min_items_sold=min_i, top_n=limit)
                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=True,
                    investigation_type=investigation_type,
                    executive_summary=res["executive_summary"],
                    metrics={"underperforming_categories_count": len(res["underperforming_categories"])},
                    evidence_data=res["underperforming_categories"],
                    causation_guardrail="High freight-to-price ratios depress net value perception, increasing propensity to leave critical ratings.",
                    recommended_action="Review shipping subsidy or carrier bundling for heavy/bulky categories with freight costs exceeding 30% of product price.",
                    execution_time_seconds=elapsed,
                )

            else:
                elapsed = round(time.time() - start_time, 3)
                return InvestigationToolOutput(
                    success=False,
                    investigation_type=investigation_type,
                    executive_summary=f"Unknown investigation type '{investigation_type}'. Supported: {self.INVESTIGATION_TYPES}",
                    metrics={},
                    evidence_data=[],
                    causation_guardrail="N/A",
                    recommended_action="Select a valid investigation type.",
                    execution_time_seconds=elapsed,
                    error=f"Unsupported investigation '{investigation_type}'.",
                )

        except Exception as e:
            logger.error(f"InvestigationTool failed on '{investigation_type}': {e}")
            elapsed = round(time.time() - start_time, 3)
            return InvestigationToolOutput(
                success=False,
                investigation_type=investigation_type,
                executive_summary="Business investigation encountered an error.",
                metrics={},
                evidence_data=[],
                causation_guardrail="N/A",
                recommended_action="Review database logs.",
                execution_time_seconds=elapsed,
                error=str(e),
            )

