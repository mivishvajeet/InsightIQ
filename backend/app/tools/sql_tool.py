"""
SQL Analytics Tool for InsightIQ Agent.

Translates natural-language questions into validated PostgreSQL queries, executes them against
the analytics star schema via the read-only user, and returns structured data and explanations.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from backend.app.services.sql_generator import SQLGenerator, SQLValidator

logger = logging.getLogger(__name__)


@dataclass
class SQLToolOutput:
    """Structured output from SQL tool execution."""
    success: bool
    question: str
    sql: str
    explanation: str
    columns: List[str]
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SQLAnalyticsTool:
    """Agent tool for querying structured PostgreSQL relational data."""

    name: str = "sql_analytics_tool"
    description: str = (
        "Translates business questions into PostgreSQL queries against the analytics schema, "
        "validates SQL AST, executes read-only queries, and returns structured table data and explanations."
    )

    def __init__(self, sql_generator: Optional[SQLGenerator] = None):
        self.generator = sql_generator or SQLGenerator()

    def run(self, question: str, sql: Optional[str] = None) -> SQLToolOutput:
        """
        Executes the SQL analytics tool. If SQL is provided, validates and executes directly;
        otherwise, generates SQL from the natural language question.
        """
        start_time = time.time()
        logger.info(f"Executing SQLAnalyticsTool for: '{question}'")

        if not sql:
            try:
                sql, df, error = self.generator.generate_and_execute(question)
            except Exception as e:
                logger.error(f"SQL generation/execution exception: {e}")
                return SQLToolOutput(
                    success=False,
                    question=question,
                    sql="",
                    explanation="Failed to generate SQL.",
                    columns=[],
                    data=[],
                    row_count=0,
                    execution_time_seconds=round(time.time() - start_time, 3),
                    error=str(e),
                )
        else:
            df, error = self.generator.execute_query(sql)

        elapsed = round(time.time() - start_time, 3)

        if error:
            return SQLToolOutput(
                success=False,
                question=question,
                sql=sql,
                explanation="SQL query failed execution.",
                columns=[],
                data=[],
                row_count=0,
                execution_time_seconds=elapsed,
                error=error,
            )

        explanation = self.generator.explain_query(question, sql)
        data_records = df.to_dict(orient="records")
        columns = list(df.columns)

        return SQLToolOutput(
            success=True,
            question=question,
            sql=sql.strip(),
            explanation=explanation,
            columns=columns,
            data=data_records,
            row_count=len(df),
            execution_time_seconds=elapsed,
            error=None,
        )
