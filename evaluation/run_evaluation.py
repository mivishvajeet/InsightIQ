"""
Benchmark Evaluation CLI for InsightIQ.

Usage:
    python -m evaluation.run_evaluation [--category "Sales Analytics"] [--limit 10]
"""

import sys
import argparse
import logging
from pathlib import Path

from evaluation.evaluator import BenchmarkEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("eval_cli")


def print_scorecard(report: dict):
    """Prints a clean ASCII scorecard summary in terminal."""
    m = report["metrics"]
    print("\n" + "=" * 70)
    print("🎯 INSIGHTIQ BENCHMARK EVALUATION SCORECARD")
    print("=" * 70)
    print(f"Timestamp:                    {report['timestamp']}")
    print(f"Total Questions Evaluated:    {report['total_questions']}")
    print(f"Passed Questions:             {report['passed_questions']}")
    print(f"Overall Pass Rate:            {report['overall_pass_rate_pct']:.2f}%")
    print("-" * 70)
    print(f"Tool-Selection Accuracy:      {m['tool_selection_accuracy_pct']:.2f}%")
    print(f"Execution Success Rate:       {m['execution_success_rate_pct']:.2f}%")
    print(f"SQL Result Correctness:       {m['sql_result_correctness_pct']:.2f}%")
    print(f"Answer Grounding:             {m['answer_grounding_pct']:.2f}%")
    print(f"Error & Security Handling:    {m['error_handling_accuracy_pct']:.2f}%")
    print(f"Average Latency:              {m['average_latency_seconds']:.2f}s")
    print(f"Total Evaluation Duration:    {m['total_duration_seconds']:.2f}s")
    print("=" * 70)

    print("\n📂 CATEGORY PERFORMANCE BREAKDOWN:")
    for cat, data in report["category_breakdown"].items():
        print(f"  • {cat:<28} {data['passed']}/{data['total']} passed ({data['pass_rate_pct']:.1f}%)")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="InsightIQ AI Agent Evaluation Benchmark")
    parser.add_argument("--category", type=str, default=None, help="Evaluate only a specific question category")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    args = parser.parse_args()

    evaluator = BenchmarkEvaluator()
    try:
        report = evaluator.run_benchmark(category=args.category, limit=args.limit)
        print_scorecard(report)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

