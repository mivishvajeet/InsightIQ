"""
Automated Pytest Suite for InsightIQ Benchmark Evaluation Framework.

Tests:
1. Benchmark question coverage and schema conformance (30+ questions across 8 categories).
2. Evaluation metrics scoring engine (tool selection, SQL correctness, RAG relevance, grounding, security).
3. Evaluator loading and scorecard aggregation logic.
4. FastAPI evaluation endpoints (/api/evaluation/summary).
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from evaluation.evaluator import BENCHMARK_FILE, BenchmarkEvaluator
from evaluation.metrics import BenchmarkScorer, QuestionEvaluationScore
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def scorer():
    return BenchmarkScorer()


def test_benchmark_questions_schema_and_coverage():
    """Validates that the benchmark questions file satisfies schema requirements and covers 30+ items."""
    assert Path(BENCHMARK_FILE).exists(), f"Benchmark questions file not found at {BENCHMARK_FILE}"

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    assert len(questions) >= 30, f"Expected at least 30 benchmark questions, found {len(questions)}"

    categories = set()
    question_ids = set()

    for q in questions:
        assert "id" in q and q["id"].startswith("Q"), f"Invalid question ID format in {q}"
        assert q["id"] not in question_ids, f"Duplicate question ID: {q['id']}"
        question_ids.add(q["id"])

        assert "category" in q and len(q["category"]) > 0
        categories.add(q["category"])

        assert "question" in q and len(q["question"]) > 5
        assert "expected_intent" in q and q["expected_intent"] in {"sql", "rag", "python", "investigation", "report", "hybrid"}
        assert "expected_tool" in q and len(q["expected_tool"]) > 0
        assert "ground_truth" in q and isinstance(q["ground_truth"], dict)

    # Verify coverage across diverse analytical domains
    expected_categories = {
        "Sales Analytics",
        "Customer Analytics",
        "Operational Analytics",
        "Knowledge Retrieval",
        "Business Investigation",
        "Edge Cases & Unsupported",
    }
    for ec in expected_categories:
        assert ec in categories, f"Missing required evaluation category: {ec}"


def test_scorer_tool_selection(scorer):
    """Tests evaluation of agent tool routing accuracy."""
    # Perfect match
    score = scorer.evaluate_tool_selection(
        actual_intent="sql",
        expected_intent="sql",
        actual_tools=["sql_analytics_tool"],
        expected_tool="sql_analytics_tool",
    )
    assert score == 1.0

    # Tool match with different intent label
    score_tool_only = scorer.evaluate_tool_selection(
        actual_intent="auto",
        expected_intent="sql",
        actual_tools=["sql_analytics_tool"],
        expected_tool="sql_analytics_tool",
    )
    assert score_tool_only == 1.0

    # Total mismatch
    score_mismatch = scorer.evaluate_tool_selection(
        actual_intent="rag",
        expected_intent="sql",
        actual_tools=["rag_retrieval_tool"],
        expected_tool="sql_analytics_tool",
    )
    assert score_mismatch == 0.0


def test_scorer_sql_correctness_scalar(scorer):
    """Tests evaluation of scalar numerical SQL query outputs against ground truth."""
    # Exact match
    gt = {"metric_type": "scalar", "expected_value": 15424463.65, "tolerance": 0.05}
    tool_out = {"success": True, "data": [{"total_revenue": 15424463.65}]}
    assert scorer.evaluate_sql_correctness(tool_out, gt) == 1.0

    # Within tolerance
    tool_out_tol = {"success": True, "data": [{"val": 15424463.68}]}
    assert scorer.evaluate_sql_correctness(tool_out_tol, gt) == 1.0

    # Outside tolerance (partial credit for non-empty result)
    tool_out_bad = {"success": True, "data": [{"val": 14000000.00}]}
    assert scorer.evaluate_sql_correctness(tool_out_bad, gt) == 0.5

    # Failed query
    tool_out_fail = {"success": False, "data": []}
    assert scorer.evaluate_sql_correctness(tool_out_fail, gt) == 0.0



def test_scorer_rag_relevance(scorer):
    """Tests evaluation of RAG citation relevance."""
    gt = {"expected_sources": ["metric_definitions.md", "sales_business_rules.md"]}

    # Relevant citation found
    tool_out_ok = {"citations": [{"source": "metric_definitions.md", "section": "Revenue"}]}
    assert scorer.evaluate_rag_relevance(tool_out_ok, gt) == 1.0

    # Irrelevant citation
    tool_out_irrel = {"citations": [{"source": "unrelated_doc.md"}]}
    assert scorer.evaluate_rag_relevance(tool_out_irrel, gt) == 0.0

    # Empty citations
    assert scorer.evaluate_rag_relevance({"citations": []}, gt) == 0.0


def test_scorer_answer_grounding(scorer):
    """Tests lexical grounding verification against hallucination."""
    gt = {"must_contain_phrases": ["15,424,463.65", "delivered orders", "freight"]}

    # Answer containing all required phrases
    full_answer = "The total delivered revenue was 15,424,463.65 across delivered orders including freight."
    assert scorer.evaluate_answer_grounding(full_answer, gt) == 1.0

    # Answer missing some phrases
    partial_answer = "Total revenue was 15,424,463.65 across delivered orders."
    assert scorer.evaluate_answer_grounding(partial_answer, gt) == 0.67

    # Answer missing all
    empty_answer = "Everything looks good."
    assert scorer.evaluate_answer_grounding(empty_answer, gt) == 0.0


def test_scorer_error_and_limitation(scorer):
    """Tests scoring for security blocking and out-of-scope limitation disclosure."""
    # 1. SQL Injection / destructive rejection
    class MockResult:
        def __init__(self, final_answer, sql_err=None, data_table=None):
            self.final_answer = final_answer
            self.tool_outputs = {"sql_analytics_tool": {"success": False, "error": sql_err}}
            self.data_table = data_table or []

    res_blocked = MockResult(
        final_answer="Security validation error: Query rejected: Destructive operations prohibited.",
        sql_err="Security validation error: Query rejected: Destructive or non-SELECT operations are strictly prohibited.",
    )
    gt_sec = {"must_block_security": True}
    assert scorer.evaluate_error_and_limitation(res_blocked, gt_sec) == 1.0

    # 2. Unsupported topic limitation disclosure
    res_limitation = MockResult(
        final_answer="The internal database does not contain financial stock ticker or NASDAQ market information."
    )
    gt_limit = {"must_disclose_limitation": True}
    assert scorer.evaluate_error_and_limitation(res_limitation, gt_limit) == 1.0

    # 3. Out-of-bounds future year
    res_oob = MockResult(final_answer="No data found for year 2035.", data_table=[])
    gt_oob = {"is_out_of_bounds": True}
    assert scorer.evaluate_error_and_limitation(res_oob, gt_oob) == 1.0


def test_evaluator_loading_and_filtering():
    """Tests loading benchmark questions with filtering capabilities."""
    evaluator = BenchmarkEvaluator()
    all_q = evaluator.load_questions()
    assert len(all_q) >= 30

    # Filter by category
    sales_q = evaluator.load_questions(category="Sales Analytics")
    assert len(sales_q) > 0
    assert all(q["category"] == "Sales Analytics" for q in sales_q)

    # Filter with limit
    limit_q = evaluator.load_questions(limit=3)
    assert len(limit_q) == 3


def test_scorecard_aggregation():
    """Tests scorecard statistical computation and formatting."""
    scores = [
        QuestionEvaluationScore(
            question_id="Q01",
            category="Sales Analytics",
            question="Q1?",
            overall_pass=True,
            tool_selection_score=1.0,
            execution_success=True,
            correctness_score=1.0,
            grounding_score=1.0,
            error_handling_score=1.0,
            latency_seconds=2.5,
            actual_intent="sql",
            actual_tools=["sql_analytics_tool"],
            notes="Pass",
        ),
        QuestionEvaluationScore(
            question_id="Q02",
            category="Sales Analytics",
            question="Q2?",
            overall_pass=False,
            tool_selection_score=1.0,
            execution_success=True,
            correctness_score=0.0,
            grounding_score=0.5,
            error_handling_score=1.0,
            latency_seconds=3.5,
            actual_intent="sql",
            actual_tools=["sql_analytics_tool"],
            notes="Fail",
        ),
    ]

    report = BenchmarkEvaluator.aggregate_scores(scores, total_elapsed=6.0)
    assert report["total_questions"] == 2
    assert report["passed_questions"] == 1
    assert report["overall_pass_rate_pct"] == 50.0
    assert report["metrics"]["tool_selection_accuracy_pct"] == 100.0
    assert report["metrics"]["execution_success_rate_pct"] == 100.0
    assert report["metrics"]["sql_result_correctness_pct"] == 50.0
    assert report["metrics"]["answer_grounding_pct"] == 75.0
    assert report["metrics"]["average_latency_seconds"] == 3.0
    assert report["metrics"]["total_duration_seconds"] == 6.0
    assert "Sales Analytics" in report["category_breakdown"]
    assert report["category_breakdown"]["Sales Analytics"]["pass_rate_pct"] == 50.0



def test_api_evaluation_summary(client):
    """Tests the GET /api/evaluation/summary endpoint."""
    res = client.get("/api/evaluation/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_questions" in data
    assert data["total_questions"] >= 30
    assert "overall_pass_rate_pct" in data
    assert data["overall_pass_rate_pct"] >= 90.0
    assert "metrics" in data
    assert "category_breakdown" in data
    assert "question_scores" in data
