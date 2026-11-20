"""
Orchestrator Agent for InsightIQ.

Main orchestrator agent that interprets user business questions, coordinates multi-step tool execution
(SQL Analytics, RAG Knowledge Retrieval, Python Analytics), captures detailed step traces,
and generates evidence-grounded business answers.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from backend.app.agents.intent_classifier import AgentIntentClassifier, IntentClassification
from backend.app.agents.synthesizer import AgentResponseSynthesizer
from backend.app.agents.memory import get_session_memory, ConversationalMemoryManager
from backend.app.tools.registry import ToolRegistry, tool_registry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """Represents an atomic execution step in the agent workflow."""
    step_number: int
    step_name: str
    tool_name: Optional[str]
    description: str
    status: str
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentExecutionResult:
    """Complete result returned by the orchestrator agent."""
    question: str
    final_answer: str
    intent: str
    tools_used: List[str]
    execution_steps: List[Dict[str, Any]]
    tool_outputs: Dict[str, Any]
    sql_query: Optional[str]
    data_table: List[Dict[str, Any]]
    columns: List[str]
    citations: List[Dict[str, Any]]
    total_execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OrchestratorAgent:
    """Single unified orchestrator agent coordinating specialized analytical tools."""

    def __init__(
        self,
        tools: Optional[ToolRegistry] = None,
        classifier: Optional[AgentIntentClassifier] = None,
        synthesizer: Optional[AgentResponseSynthesizer] = None,
    ):
        self.tools = tools or tool_registry
        self.classifier = classifier or AgentIntentClassifier()
        self.synthesizer = synthesizer or AgentResponseSynthesizer()

    def run(
        self,
        question: str,
        mode_override: Optional[str] = None,
        top_k: int = 4,
        session_id: str = "default_session",
    ) -> AgentExecutionResult:
        """
        Executes the multi-step agent orchestration workflow for a natural language question.
        Supports automatic intent classification or explicit mode override (sql, rag, python, hybrid),
        and maintains conversational context memory across session turns.
        """
        start_overall = time.time()
        logger.info(f"Orchestrator received question: '{question}' (mode_override={mode_override}, session={session_id})")

        memory = get_session_memory(session_id)
        steps: List[ExecutionStep] = []
        tool_outputs: Dict[str, Any] = {}
        tools_used: List[str] = []
        sql_query: Optional[str] = None
        data_table: List[Dict[str, Any]] = []
        columns: List[str] = []
        citations: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # STEP 1: Intent Classification & Tool Planning
        # -------------------------------------------------------------
        t0 = time.time()
        if mode_override and mode_override != "auto":
            override_map = {
                "sql": ["sql_analytics_tool"],
                "rag": ["rag_retrieval_tool"],
                "python": ["python_analytics_tool"],
                "hybrid": ["rag_retrieval_tool", "sql_analytics_tool"],
                "investigation": ["business_investigation_tool"],
                "report": ["report_generation_tool"],
            }
            tools_plan = override_map.get(mode_override.lower(), ["sql_analytics_tool"])
            classification = IntentClassification(
                intent=mode_override.lower(),
                tools_required=tools_plan,
                confidence=1.0,
                reasoning=f"User explicitly selected '{mode_override}' execution mode.",
            )
            effective_question = question
        else:
            classification = self.classifier.classify(question, memory=memory)
            effective_question = classification.rewritten_query or question

        duration_step1 = round(time.time() - t0, 3)
        if classification.rewritten_query:
            steps.append(
                ExecutionStep(
                    step_number=1,
                    step_name="Conversational Query Rewriting",
                    tool_name=None,
                    description=f"Resolved follow-up question to: '{effective_question}'",
                    status="completed",
                    duration_seconds=duration_step1,
                )
            )

        steps.append(
            ExecutionStep(
                step_number=len(steps) + 1,
                step_name="Intent Planning",
                tool_name=None,
                description=f"Classified intent as '{classification.intent}'. Planning tools: {classification.tools_required}. ({classification.reasoning})",
                status="completed",
                duration_seconds=duration_step1,
            )
        )

        # -------------------------------------------------------------
        # STEP 2: Tool Execution Sequence
        # -------------------------------------------------------------
        for tool_name in classification.tools_required:
            step_num = len(steps) + 1
            t_tool = time.time()

            try:
                if tool_name == "sql_analytics_tool":
                    output = self.tools.execute_tool("sql_analytics_tool", question=effective_question)
                    tool_outputs["sql_analytics_tool"] = output
                    tools_used.append("sql_analytics_tool")

                    if output.get("success"):
                        sql_query = output.get("sql")
                        data_table = output.get("data", [])
                        columns = output.get("columns", [])
                        desc = f"Executed SQL against PostgreSQL: returned {output.get('row_count')} rows."
                        status = "completed"
                    else:
                        desc = f"SQL execution error: {output.get('error')}"
                        status = "failed"

                elif tool_name == "rag_retrieval_tool":
                    output = self.tools.execute_tool(
                        "rag_retrieval_tool",
                        query=effective_question,
                        top_k=top_k,
                        synthesize_answer=True,
                    )
                    tool_outputs["rag_retrieval_tool"] = output
                    tools_used.append("rag_retrieval_tool")

                    if output.get("success"):
                        citations.extend(output.get("citations", []))
                        desc = f"Retrieved {output.get('total_found')} documentation chunks with semantic citations."
                        status = "completed"
                    else:
                        desc = f"RAG retrieval error: {output.get('error')}"
                        status = "failed"

                elif tool_name == "python_analytics_tool":
                    operation = classification.suggested_python_operation or "executive_summary"
                    output = self.tools.execute_tool("python_analytics_tool", operation=operation)
                    tool_outputs["python_analytics_tool"] = output
                    tools_used.append("python_analytics_tool")

                    if output.get("success"):
                        data_table = output.get("data", [])
                        if data_table and isinstance(data_table[0], dict):
                            columns = list(data_table[0].keys())
                        desc = f"Executed Python analytics operation '{operation}': {output.get('summary')}"
                        status = "completed"
                    else:
                        desc = f"Python analytics error: {output.get('error')}"
                        status = "failed"

                elif tool_name == "business_investigation_tool":
                    inv_type = classification.suggested_python_operation or "revenue_anomaly"
                    output = self.tools.execute_tool("business_investigation_tool", investigation_type=inv_type)
                    tool_outputs["business_investigation_tool"] = output
                    tools_used.append("business_investigation_tool")

                    if output.get("success"):
                        data_table = output.get("evidence_data", [])
                        if data_table and isinstance(data_table[0], dict):
                            columns = list(data_table[0].keys())
                        desc = f"Executed Business Investigation '{inv_type}': {output.get('executive_summary')[:100]}..."
                        status = "completed"
                    else:
                        desc = f"Investigation error: {output.get('error')}"
                        status = "failed"

                elif tool_name == "report_generation_tool":
                    output = self.tools.execute_tool("report_generation_tool", report_type="executive_summary")
                    tool_outputs["report_generation_tool"] = output
                    tools_used.append("report_generation_tool")

                    if output.get("success"):
                        desc = f"Compiled formal business report: {output.get('report_title')}"
                        status = "completed"
                    else:
                        desc = f"Report generation error: {output.get('error')}"
                        status = "failed"

                else:
                    desc = f"Skipping unrecognized tool '{tool_name}'."
                    status = "skipped"

            except Exception as e:
                logger.error(f"Error during step for tool '{tool_name}': {e}")
                desc = f"Exception executing tool: {e}"
                status = "failed"

            steps.append(
                ExecutionStep(
                    step_number=step_num,
                    step_name=f"Execute {tool_name}",
                    tool_name=tool_name,
                    description=desc,
                    status=status,
                    duration_seconds=round(time.time() - t_tool, 3),
                )
            )

        # -------------------------------------------------------------
        # STEP 3: Evidence-Grounded Synthesis
        # -------------------------------------------------------------
        t_synth = time.time()
        final_answer = self.synthesizer.synthesize(
            question=effective_question,
            tool_outputs=tool_outputs,
            intent=classification.intent,
        )
        duration_synth = round(time.time() - t_synth, 3)

        steps.append(
            ExecutionStep(
                step_number=len(steps) + 1,
                step_name="Response Synthesis",
                tool_name=None,
                description="Synthesized multi-tool evidence into structured executive response.",
                status="completed",
                duration_seconds=duration_synth,
            )
        )

        total_elapsed = round(time.time() - start_overall, 3)

        # Record completed interaction in session memory
        memory.add_turn(
            user_query=question,
            final_answer=final_answer,
            intent=classification.intent,
            tools_used=tools_used,
            sql_query=sql_query,
            rewritten_query=classification.rewritten_query,
        )

        return AgentExecutionResult(
            question=question,
            final_answer=final_answer,
            intent=classification.intent,
            tools_used=tools_used,
            execution_steps=[s.to_dict() for s in steps],
            tool_outputs=tool_outputs,
            sql_query=sql_query,
            data_table=data_table,
            columns=columns,
            citations=citations,
            total_execution_time_seconds=total_elapsed,
            error=None,
        )


# Singleton orchestrator agent
orchestrator_agent = OrchestratorAgent()
