"""
Report Generation Tool for InsightIQ Agent.

Generates formal business performance reports, weekly summaries, and investigation dossiers
in Markdown and structured JSON for presentation and export.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from backend.app.reporting.report_generator import ReportGeneratorService

logger = logging.getLogger(__name__)


@dataclass
class ReportToolOutput:
    """Structured output from report generation tool."""
    success: bool
    report_title: str
    markdown_content: str
    metadata: Dict[str, Any]
    execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReportGenerationTool:
    """Agent tool for generating structured executive business performance reports."""

    name: str = "report_generation_tool"
    description: str = (
        "Generates formal executive business reports, weekly operational summaries, and exportable "
        "markdown reports containing key KPIs, customer satisfaction drivers, and strategic recommendations."
    )

    def __init__(self, service: Optional[ReportGeneratorService] = None):
        self.service = service or ReportGeneratorService()

    def run(self, report_type: str = "executive_summary") -> ReportToolOutput:
        """
        Executes report compilation and formatting.
        """
        start_time = time.time()
        logger.info(f"Executing ReportGenerationTool for type: '{report_type}'")

        try:
            report_data = self.service.generate_executive_business_report()
            elapsed = round(time.time() - start_time, 3)

            return ReportToolOutput(
                success=True,
                report_title=report_data["title"],
                markdown_content=report_data["markdown"],
                metadata={
                    "timestamp": report_data["timestamp"],
                    "sections": report_data["sections"],
                },
                execution_time_seconds=elapsed,
            )
        except Exception as e:
            logger.error(f"ReportGenerationTool failed: {e}")
            elapsed = round(time.time() - start_time, 3)
            return ReportToolOutput(
                success=False,
                report_title="Report Generation Failed",
                markdown_content="",
                metadata={},
                execution_time_seconds=elapsed,
                error=str(e),
            )

