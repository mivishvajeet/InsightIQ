"""
Agent Intent Classifier for InsightIQ.

Classifies incoming natural-language business questions into appropriate tool execution plans
(SQL, RAG, Python Analytics, or Hybrid multi-tool workflows) using domain heuristics and LLM inference.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from backend.app.services.llm_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class IntentClassification:
    """Classified user intent and recommended tool execution pipeline."""
    intent: str  # "sql", "rag", "python", "hybrid"
    tools_required: List[str]
    confidence: float
    reasoning: str
    suggested_python_operation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentIntentClassifier:
    """Classifies user query intent and determines tool orchestration requirements."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm = llm_client or OllamaClient()

    def classify(self, question: str) -> IntentClassification:
        """
        Determines the intent and tool requirements for a given question.
        Combines pattern-based semantic heuristics with LLM fallback.
        """
        q_lower = question.lower().strip()

        # 1. RAG Heuristics: Definitions, formulas, schema, policy explanations
        rag_patterns = [
            r"^(what is|what does|how is|explain|define|tell me about)\s+(the\s+)?(definition|meaning|formula|calculation|policy|sla|schema|star schema)",
            r"(how is|how do we calculate|how to calculate)\s+",
            r"(definition of|meaning of|what does .* mean)",
            r"explain the database",
            r"delivery policies|cancellation policy",
        ]
        is_rag_candidate = any(re.search(pat, q_lower) for pat in rag_patterns)

        # 2. Python Analytics Heuristics: Specific statistical operations
        if any(kw in q_lower for kw in ["anomaly", "anomalies", "outlier", "spike", "black friday"]):
            return IntentClassification(
                intent="python",
                tools_required=["python_analytics_tool"],
                confidence=0.95,
                reasoning="Detected statistical anomaly/outlier detection request.",
                suggested_python_operation="revenue_anomalies",
            )

        if any(kw in q_lower for kw in ["correlation", "pearson", "spearman", "correlated"]):
            return IntentClassification(
                intent="python",
                tools_required=["python_analytics_tool"],
                confidence=0.95,
                reasoning="Detected statistical correlation analysis request.",
                suggested_python_operation="delivery_correlation",
            )

        if "rfm" in q_lower or "customer segmentation" in q_lower:
            return IntentClassification(
                intent="python",
                tools_required=["python_analytics_tool"],
                confidence=0.92,
                reasoning="Detected customer RFM segmentation request.",
                suggested_python_operation="customer_rfm",
            )

        # 3. Hybrid Heuristics: Asking for definition AND actual live metrics
        if is_rag_candidate and any(kw in q_lower for kw in ["and how many", "and what is our", "and calculate", "and show data", "actual"]):
            return IntentClassification(
                intent="hybrid",
                tools_required=["rag_retrieval_tool", "sql_analytics_tool"],
                confidence=0.90,
                reasoning="Detected dual request for business definition and live database metrics.",
            )

        # Pure RAG
        if is_rag_candidate:
            return IntentClassification(
                intent="rag",
                tools_required=["rag_retrieval_tool"],
                confidence=0.92,
                reasoning="Detected knowledge base query regarding metric definitions, policies, or schema rules.",
            )

        # 4. Standard SQL Data Analytics Heuristics
        sql_keywords = [
            "revenue", "sales", "orders", "aov", "average order value",
            "trend", "monthly", "category", "categories", "seller", "sellers",
            "customer", "customers", "repeat purchase", "state", "states",
            "top", "highest", "lowest", "count", "sum", "average", "avg",
            "cancellation rate", "review score",
        ]
        if any(kw in q_lower for kw in sql_keywords):
            return IntentClassification(
                intent="sql",
                tools_required=["sql_analytics_tool"],
                confidence=0.90,
                reasoning="Detected quantitative data analytics question suited for PostgreSQL query execution.",
            )

        # Default fallback to SQL analytics
        return IntentClassification(
            intent="sql",
            tools_required=["sql_analytics_tool"],
            confidence=0.75,
            reasoning="Defaulted to SQL analytics tool for structured data exploration.",
        )
