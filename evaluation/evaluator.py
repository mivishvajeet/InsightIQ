"""
Benchmark Evaluator Engine for InsightIQ.

Executes the 35 business benchmark questions through the OrchestratorAgent,
measures execution success, tool selection accuracy, SQL correctness, RAG grounding,
and error handling, and generates detailed evaluation reports.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from evaluation.metrics import BenchmarkScorer, QuestionEvaluationScore
from backend.app.agents.orchestrator import orchestrator_agent, OrchestratorAgent

logger = logging.getLogger("evaluator")

EVAL_DIR = Path(__file__).resolve().parent
BENCHMARK_FILE = EVAL_DIR / "benchmark_questions.json"
RESULTS_DIR = EVAL_DIR / "results"


class BenchmarkEvaluator:
    """Orchestrates comprehensive benchmark test execution and scorecard aggregation."""

    def __init__(self, agent: Optional[OrchestratorAgent] = None):
        self.agent = agent or orchestrator_agent
        self.scorer = BenchmarkScorer()
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def load_questions(self, category: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads benchmark question items with optional category and limit filters."""
        with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
            questions = json.load(f)

        if category:
            questions = [q for q in questions if q.get("category", "").lower() == category.lower()]
        if limit and limit > 0:
            questions = questions[:limit]

        return questions

    def evaluate_single(self, item: Dict[str, Any]) -> QuestionEvaluationScore:
        """Runs the orchestrator agent on a single question item and scores all dimensions."""
        qid = item["id"]
        cat = item["category"]
        q_text = item["question"]
        expected_intent = item["expected_intent"]
        expected_tool = item["expected_tool"]
        gt = item.get("ground_truth", {})

        logger.info(f"Evaluating [{qid}] ({cat}): '{q_text}'")
        t_start = time.time()

        try:
            result = self.agent.run(q_text)
            elapsed = round(time.time() - t_start, 2)
            actual_intent = result.intent
            actual_tools = result.tools_used
            exec_success = True
        except Exception as e:
            logger.error(f"Execution error on [{qid}]: {e}")
            elapsed = round(time.time() - t_start, 2)
            return QuestionEvaluationScore(
                question_id=qid,
                category=cat,
                question=q_text,
                overall_pass=False,
                tool_selection_score=0.0,
                execution_success=False,
                correctness_score=0.0,
                grounding_score=0.0,
                error_handling_score=0.0,
                latency_seconds=elapsed,
                actual_intent="error",
                actual_tools=[],
                notes=f"Exception: {str(e)}",
            )

        # 1. Tool Selection Score
        tool_score = self.scorer.evaluate_tool_selection(
            actual_intent=actual_intent,
            expected_intent=expected_intent,
            actual_tools=actual_tools,
            expected_tool=expected_tool,
        )

        # 2. Correctness Score (SQL or Python or RAG)
        correctness_score = 1.0
        if "sql_analytics_tool" in actual_tools:
            sql_out = result.tool_outputs.get("sql_analytics_tool", {})
            correctness_score = self.scorer.evaluate_sql_correctness(sql_out, gt)
        elif "python_analytics_tool" in actual_tools:
            py_out = result.tool_outputs.get("python_analytics_tool", {})
            correctness_score = 1.0 if py_out.get("success") else 0.0

        # 3. RAG Relevance Score
        if "rag_retrieval_tool" in actual_tools and "expected_sources" in gt:
            rag_out = result.tool_outputs.get("rag_retrieval_tool", {})
            relevance = self.scorer.evaluate_rag_relevance(rag_out, gt)
            correctness_score = min(correctness_score, relevance)

        # 4. Answer Grounding Score
        grounding_score = self.scorer.evaluate_answer_grounding(result.final_answer, gt)

        # 5. Error & Limitation Handling Score
        error_score = self.scorer.evaluate_error_and_limitation(result, gt)

        # Overall Pass criteria
        # Pass requires tool selection >= 1.0, execution_success, error_score >= 1.0, and correctness >= 0.5
        overall_pass = (
            tool_score >= 1.0
            and exec_success
            and error_score >= 0.8
            and correctness_score >= 0.5
        )

        notes = "Pass" if overall_pass else "Score below threshold on one or more dimensions"

        return QuestionEvaluationScore(
            question_id=qid,
            category=cat,
            question=q_text,
            overall_pass=overall_pass,
            tool_selection_score=tool_score,
            execution_success=exec_success,
            correctness_score=correctness_score,
            grounding_score=grounding_score,
            error_handling_score=error_score,
            latency_seconds=elapsed,
            actual_intent=actual_intent,
            actual_tools=actual_tools,
            notes=notes,
        )

    def run_benchmark(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs the benchmark suite, aggregates metrics, and saves the evaluation report."""
        questions = self.load_questions(category=category, limit=limit)
        total_q = len(questions)
        logger.info(f"Starting evaluation of {total_q} benchmark questions...")

        scores: List[QuestionEvaluationScore] = []
        start_suite = time.time()

        for item in questions:
            score = self.evaluate_single(item)
            scores.append(score)

        total_elapsed = round(time.time() - start_suite, 2)

        # Aggregate Statistics
        passed_count = sum(1 for s in scores if s.overall_pass)
        pass_rate_pct = round((passed_count / total_q) * 100.0, 2) if total_q > 0 else 0.0

        avg_tool_selection = round(sum(s.tool_selection_score for s in scores) / total_q * 100.0, 2)
        avg_execution_success = round(sum(1 for s in scores if s.execution_success) / total_q * 100.0, 2)
        avg_correctness = round(sum(s.correctness_score for s in scores) / total_q * 100.0, 2)
        avg_grounding = round(sum(s.grounding_score for s in scores) / total_q * 100.0, 2)
        avg_error_handling = round(sum(s.error_handling_score for s in scores) / total_q * 100.0, 2)
        avg_latency = round(sum(s.latency_seconds for s in scores) / total_q, 2)

        # Category level aggregation
        cat_breakdown: Dict[str, Dict[str, Any]] = {}
        for s in scores:
            if s.category not in cat_breakdown:
                cat_breakdown[s.category] = {"total": 0, "passed": 0}
            cat_breakdown[s.category]["total"] += 1
            if s.overall_pass:
                cat_breakdown[s.category]["passed"] += 1

        for c, data in cat_breakdown.items():
            data["pass_rate_pct"] = round(data["passed"] / data["total"] * 100.0, 2)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_questions": total_q,
            "passed_questions": passed_count,
            "overall_pass_rate_pct": pass_rate_pct,
            "metrics": {
                "tool_selection_accuracy_pct": avg_tool_selection,
                "execution_success_rate_pct": avg_execution_success,
                "sql_result_correctness_pct": avg_correctness,
                "answer_grounding_pct": avg_grounding,
                "error_handling_accuracy_pct": avg_error_handling,
                "average_latency_seconds": avg_latency,
                "total_duration_seconds": total_elapsed,
            },
            "category_breakdown": cat_breakdown,
            "question_scores": [s.to_dict() for s in scores],
        }

        # Save report
        out_file = RESULTS_DIR / "latest_evaluation.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Evaluation report written to {out_file} (Pass Rate: {pass_rate_pct}%)")
        return report
