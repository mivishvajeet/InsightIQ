"""
Benchmark Failure Analysis & Self-Healing Recommendations Engine for InsightIQ.

Analyzes failed or sub-optimal questions from benchmark evaluation runs,
categorizes root causes across routing, SQL generation, grounding, and latency,
and produces actionable self-healing recommendations for continuous model improvement.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("failure_analysis")

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_FILE = EVAL_DIR / "results" / "latest_evaluation.json"


class FailureAnalyzer:
    """Diagnoses evaluation failures and generates self-healing recommendations."""

    def __init__(self, evaluation_file: Optional[Path] = None):
        self.file_path = evaluation_file or RESULTS_FILE

    def load_evaluation(self) -> Dict[str, Any]:
        """Loads the latest evaluation report from disk."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Evaluation report not found at {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def analyze(self) -> Dict[str, Any]:
        """Performs comprehensive root-cause analysis on all failed or borderline questions."""
        data = self.load_evaluation()
        scores = data.get("question_scores", [])
        total_q = len(scores)
        passed_q = data.get("passed_questions", 0)
        overall_pass_rate = data.get("overall_pass_rate_pct", 0.0)

        failures: List[Dict[str, Any]] = []
        latency_outliers: List[Dict[str, Any]] = []
        category_deficits: Dict[str, int] = {}

        for item in scores:
            qid = item.get("question_id")
            cat = item.get("category")
            q_text = item.get("question")
            overall_pass = item.get("overall_pass")
            latency = item.get("latency_seconds", 0.0)

            # Check latency bottleneck (> 15 seconds)
            if latency > 15.0:
                latency_outliers.append({
                    "question_id": qid,
                    "category": cat,
                    "question": q_text,
                    "latency_seconds": latency,
                })

            if not overall_pass:
                category_deficits[cat] = category_deficits.get(cat, 0) + 1

                # Diagnose primary failure reason
                root_causes = []
                recommendations = []

                if item.get("tool_selection_score", 1.0) < 1.0:
                    root_causes.append("Tool Routing Failure: Orchestrator failed to dispatch the expected analytical tool.")
                    recommendations.append("Add domain-specific regex heuristics or few-shot intent exemplars in AgentIntentClassifier.")

                if not item.get("execution_success", True):
                    root_causes.append("Execution Exception: The invoked tool encountered an unhandled runtime error.")
                    recommendations.append("Ensure database connection pools and Ollama API endpoints are active and resilient.")

                if item.get("correctness_score", 1.0) < 0.5:
                    root_causes.append("Correctness Deficit: Result did not match ground truth baseline (SQL filter, join, or aggregation error).")
                    recommendations.append("Inject a dedicated SQL exemplar into sql_generator.py FEW-SHOT QUERY EXEMPLARS.")

                if item.get("grounding_score", 1.0) < 0.5:
                    root_causes.append("Grounding Deficiency: Synthesized answer missed key quantitative facts or business terms.")
                    recommendations.append("Strengthen synthesis prompt with strict grounding instructions to enforce citing retrieved table values.")

                if item.get("error_handling_score", 1.0) < 0.8:
                    root_causes.append("Security / Limitation Guardrail Flaw: Malicious query not properly rejected or out-of-scope query not disclosed.")
                    recommendations.append("Refine SQLValidator AST security rules or add limitation disclosure heuristics.")

                failures.append({
                    "question_id": qid,
                    "category": cat,
                    "question": q_text,
                    "actual_intent": item.get("actual_intent"),
                    "actual_tools": item.get("actual_tools"),
                    "tool_score": item.get("tool_selection_score"),
                    "correctness_score": item.get("correctness_score"),
                    "grounding_score": item.get("grounding_score"),
                    "error_score": item.get("error_handling_score"),
                    "latency_seconds": latency,
                    "root_causes": root_causes,
                    "recommendations": recommendations,
                    "notes": item.get("notes"),
                })

        return {
            "timestamp": data.get("timestamp"),
            "total_questions": total_q,
            "passed_questions": passed_q,
            "failed_questions": len(failures),
            "overall_pass_rate_pct": overall_pass_rate,
            "category_deficits": category_deficits,
            "failures": failures,
            "latency_outliers": latency_outliers,
            "summary_recommendations": self._generate_strategic_recommendations(failures),
        }

    def _generate_strategic_recommendations(self, failures: List[Dict[str, Any]]) -> List[str]:
        """Compiles overarching architectural and prompt-engineering recommendations."""
        if not failures:
            return ["All benchmark questions achieved passing scores. Benchmark suite health is optimal (>90% pass rate)."]

        recs = set()
        for f in failures:
            for r in f.get("recommendations", []):
                recs.add(r)

        return sorted(list(recs))

    def print_report(self):
        """Prints a human-readable failure analysis report to console."""
        analysis = self.analyze()
        print("\n" + "=" * 70)
        print("🔍 INSIGHTIQ BENCHMARK FAILURE & ROOT-CAUSE ANALYSIS")
        print("=" * 70)
        print(f"Timestamp:                 {analysis['timestamp']}")
        print(f"Total Questions:           {analysis['total_questions']}")
        print(f"Passed:                    {analysis['passed_questions']}")
        print(f"Failed:                    {analysis['failed_questions']}")
        print(f"Overall Pass Rate:         {analysis['overall_pass_rate_pct']}%")
        print("-" * 70)

        if analysis["category_deficits"]:
            print("📉 FAILURES BY CATEGORY:")
            for cat, count in analysis["category_deficits"].items():
                print(f"  • {cat:<28} {count} failures")
            print("-" * 70)

        if analysis["failures"]:
            print("🚨 DETAILED FAILURE INVESTIGATIONS:")
            for f in analysis["failures"]:
                print(f"\n[{f['question_id']}] ({f['category']}): '{f['question']}'")
                print(f"  Tools: {f['actual_tools']} | Intent: {f['actual_intent']} | Latency: {f['latency_seconds']}s")
                for rc in f["root_causes"]:
                    print(f"  ❌ {rc}")
                for rec in f["recommendations"]:
                    print(f"  💡 Fix: {rec}")
            print("-" * 70)
        else:
            print("🎉 Zero test failures detected! 100% of benchmark questions passed.")

        if analysis["latency_outliers"]:
            print("⏱️ LATENCY OUTLIERS (>15s):")
            for lo in analysis["latency_outliers"]:
                print(f"  • [{lo['question_id']}] {lo['latency_seconds']}s - '{lo['question']}'")
            print("-" * 70)

        print("🛠️ STRATEGIC RECOMMENDATIONS:")
        for r in analysis["summary_recommendations"]:
            print(f"  → {r}")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    analyzer = FailureAnalyzer()
    analyzer.print_report()
