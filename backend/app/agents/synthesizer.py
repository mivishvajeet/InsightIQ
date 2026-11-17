"""
Agent Response Synthesizer for InsightIQ.

Combines outputs from multiple specialized tools (SQL execution, RAG knowledge retrieval,
Python statistical computations) into a cohesive, evidence-backed executive summary.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.app.services.llm_client import OllamaClient

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """You are InsightIQ, an expert Business Intelligence Agent for the Brazilian E-Commerce platform Olist.

Your task is to synthesize tool outputs into a clear, grounded, professional executive answer for the user.

RULES:
1. ONLY cite facts, metrics, rows, or definitions directly present in the TOOL OUTPUTS below.
2. NEVER invent numbers, SQL execution results, or business facts.
3. If correlation analysis is included, explicitly state: "Correlation does not imply causation."
4. If SQL data is present, mention key metrics, top items, and total volume.
5. If RAG citations are present, attribute findings to the source documents.
6. Format your answer with:
   - **Executive Takeaway** (1-2 sentences)
   - **Detailed Analytical Findings** (bullet points with concrete numbers)
   - **Business Context / Policies** (if RAG context was used)
   - **Recommended Next Investigation** (1 actionable next step)
"""


class AgentResponseSynthesizer:
    """Synthesizes multi-tool outputs into a unified grounded business answer."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm = llm_client or OllamaClient()

    def synthesize(
        self,
        question: str,
        tool_outputs: Dict[str, Any],
        intent: str,
    ) -> str:
        """
        Synthesizes a final response using Qwen 2.5 3B based on the collected tool outputs.
        """
        # If pure Report and markdown already compiled, return directly
        if intent == "report" and "report_generation_tool" in tool_outputs:
            rep_out = tool_outputs["report_generation_tool"]
            if rep_out.get("markdown_content"):
                return rep_out["markdown_content"]

        # If pure RAG and answer already exists, return with minor polishing or directly
        if intent == "rag" and "rag_retrieval_tool" in tool_outputs:
            rag_out = tool_outputs["rag_retrieval_tool"]
            if rag_out.get("answer"):
                return rag_out["answer"]

        # Build context summary from tool outputs
        context_parts = []

        if "business_investigation_tool" in tool_outputs:
            inv_out = tool_outputs["business_investigation_tool"]
            context_parts.append(
                f"--- BUSINESS INVESTIGATION TOOL OUTPUT ---\n"
                f"Investigation Type: {inv_out.get('investigation_type')}\n"
                f"Executive Summary: {inv_out.get('executive_summary')}\n"
                f"Key Metrics: {inv_out.get('metrics')}\n"
                f"Causation Guardrail: {inv_out.get('causation_guardrail')}\n"
                f"Recommended Action: {inv_out.get('recommended_action')}"
            )

        if "sql_analytics_tool" in tool_outputs:
            sql_out = tool_outputs["sql_analytics_tool"]
            if sql_out.get("success"):
                sample_data = sql_out.get("data", [])[:5]
                context_parts.append(
                    f"--- SQL ANALYTICS TOOL OUTPUT ---\n"
                    f"Generated SQL: {sql_out.get('sql')}\n"
                    f"Rows Returned: {sql_out.get('row_count')}\n"
                    f"Columns: {sql_out.get('columns')}\n"
                    f"Sample Rows: {sample_data}\n"
                    f"SQL Explanation: {sql_out.get('explanation')}"
                )
            else:
                context_parts.append(f"SQL Tool Error: {sql_out.get('error')}")

        if "rag_retrieval_tool" in tool_outputs:
            rag_out = tool_outputs["rag_retrieval_tool"]
            citations = [f"[{c['source']} - {c['section']}]: {c['snippet']}" for c in rag_out.get("citations", [])]
            context_parts.append(
                f"--- RAG KNOWLEDGE RETRIEVAL OUTPUT ---\n"
                f"Retrieved Citations:\n" + "\n".join(citations)
            )

        if "python_analytics_tool" in tool_outputs:
            py_out = tool_outputs["python_analytics_tool"]
            context_parts.append(
                f"--- PYTHON ANALYTICS TOOL OUTPUT ---\n"
                f"Operation: {py_out.get('operation')}\n"
                f"Summary: {py_out.get('summary')}\n"
                f"Key Metrics: {py_out.get('metrics')}"
            )

        combined_tool_context = "\n\n".join(context_parts)

        user_prompt = f"""USER QUESTION:
{question}

TOOL OUTPUTS:
{combined_tool_context}

Provide a structured, evidence-grounded answer following the rules."""

        try:
            return self.llm.generate(
                prompt=user_prompt,
                system_prompt=SYNTHESIS_PROMPT,
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback deterministic summary
            return (
                f"Analysis completed for: '{question}'.\n\n"
                + "\n\n".join([f"**{tool}**: {out.get('summary', out.get('explanation', 'Success'))}"
                              for tool, out in tool_outputs.items() if isinstance(out, dict)])
            )
