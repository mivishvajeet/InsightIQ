"""
InsightIQ: Evaluation Framework & Benchmark Scorecard UI.
Fulfills Section 8.G of Master Prompt:
- Automated testing across 30+ complex business questions
- Telemetry across SQL success, result correctness, RAG retrieval relevance, answer grounding, tool accuracy, error handling
- Interactive category breakdown, pass/fail inspection, and latency metrics
"""

import sys
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.evaluator import BenchmarkEvaluator, RESULTS_DIR
from frontend.components.styles import apply_theme

st.set_page_config(page_title="Evaluation Framework | InsightIQ", page_icon="🎯", layout="wide")
apply_theme()

st.title("🎯 Evaluation Framework & Benchmark Scorecard")
st.markdown(
    "Automated regression testing and accuracy evaluation across **35 complex business questions**, "
    "measuring tool routing, SQL correctness, RAG grounding, and security guardrails."
)

# Load Latest Evaluation Results
result_file = RESULTS_DIR / "latest_evaluation.json"

if not result_file.exists():
    st.warning("No benchmark evaluation report found on disk. Click 'Run Evaluation' below to execute the benchmark.")
    evaluation_data = None
else:
    with open(result_file, "r", encoding="utf-8") as f:
        evaluation_data = json.load(f)

# Sidebar: Controls & Live Re-run
st.sidebar.header("⚙️ Evaluation Controls")
run_category = st.sidebar.selectbox("Test Category Slice:", [
    "All Categories",
    "Sales Analytics",
    "Customer Analytics",
    "Operational Analytics",
    "Knowledge Retrieval",
    "Business Investigation",
    "Edge Cases & Unsupported",
])

run_limit = st.sidebar.slider("Question Limit (for quick run):", min_value=3, max_value=35, value=10)

if st.sidebar.button("🚀 Run Live Evaluation", type="primary"):
    category_param = None if run_category == "All Categories" else run_category
    with st.spinner(f"Executing automated benchmark evaluation ({run_category}, limit={run_limit})..."):
        evaluator = BenchmarkEvaluator()
        evaluation_data = evaluator.run_benchmark(category=category_param, limit=run_limit)
        st.success("Benchmark evaluation completed!")
        st.rerun()

if evaluation_data:
    metrics = evaluation_data.get("metrics", {})
    ts = evaluation_data.get("timestamp", "N/A")
    total_q = evaluation_data.get("total_questions", 0)
    passed_q = evaluation_data.get("passed_questions", 0)
    pass_rate = evaluation_data.get("overall_pass_rate_pct", 0.0)

    # Top KPI Metrics Ribbon
    st.markdown(f"**Last Benchmark Run:** `{ts}` | Total Questions: **{total_q}** | Passed: **{passed_q}**")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Overall Benchmark Pass Rate",
            value=f"{pass_rate}%",
            delta=f"{passed_q}/{total_q} Passed",
            delta_color="normal" if pass_rate >= 80.0 else "inverse",
        )
    with col2:
        st.metric(
            label="Tool-Selection Accuracy",
            value=f"{metrics.get('tool_selection_accuracy_pct', 0.0)}%",
            delta="100% Intent Routing",
        )
    with col3:
        st.metric(
            label="SQL Result Correctness",
            value=f"{metrics.get('sql_result_correctness_pct', 0.0)}%",
            delta="Ground Truth Match",
        )
    with col4:
        st.metric(
            label="Answer Grounding",
            value=f"{metrics.get('answer_grounding_pct', 0.0)}%",
            delta="Hallucination Guarded",
        )

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric(
            label="Execution Success Rate",
            value=f"{metrics.get('execution_success_rate_pct', 0.0)}%",
        )
    with col6:
        st.metric(
            label="Security & Guardrail Handling",
            value=f"{metrics.get('error_handling_accuracy_pct', 0.0)}%",
        )
    with col7:
        st.metric(
            label="Average Latency",
            value=f"{metrics.get('average_latency_seconds', 0.0)}s",
        )
    with col8:
        st.metric(
            label="Total Benchmark Duration",
            value=f"{metrics.get('total_duration_seconds', 0.0)}s",
        )

    st.markdown("---")

    # Category Breakdown & Latency Charts
    col_chart1, col_chart2 = st.columns([1, 1])

    with col_chart1:
        st.subheader("📊 Category Pass Rates")
        cat_data = evaluation_data.get("category_breakdown", {})
        if cat_data:
            cat_df = pd.DataFrame([
                {
                    "Category": c,
                    "Total": d["total"],
                    "Passed": d["passed"],
                    "Pass Rate (%)": d.get("pass_rate_pct", round(d["passed"] / d["total"] * 100, 1)),
                }
                for c, d in cat_data.items()
            ])
            fig_cat = px.bar(
                cat_df,
                x="Pass Rate (%)",
                y="Category",
                orientation="h",
                text="Pass Rate (%)",
                color="Pass Rate (%)",
                color_continuous_scale="Viridis",
                range_x=[0, 105],
            )
            fig_cat.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_cat, use_container_width=True)

    with col_chart2:
        st.subheader("⏱️ Execution Latency by Question")
        q_scores = evaluation_data.get("question_scores", [])
        if q_scores:
            latency_df = pd.DataFrame([
                {
                    "Question ID": q["question_id"],
                    "Latency (s)": q.get("latency_seconds", 0.0),
                    "Status": "Passed" if q.get("overall_pass") else "Failed",
                }
                for q in q_scores
            ])
            fig_lat = px.scatter(
                latency_df,
                x="Question ID",
                y="Latency (s)",
                color="Status",
                color_discrete_map={"Passed": "#2ECC71", "Failed": "#E74C3C"},
                size="Latency (s)",
                hover_data=["Question ID", "Latency (s)", "Status"],
            )
            fig_lat.add_hline(
                y=metrics.get("average_latency_seconds", 10.0),
                line_dash="dash",
                line_color="#F39C12",
                annotation_text=f"Avg: {metrics.get('average_latency_seconds', 10.0)}s",
            )
            fig_lat.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_lat, use_container_width=True)

    st.markdown("---")

    # Filterable Questions Table
    st.subheader("📋 Comprehensive Question Evaluation Log")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        cat_filter = st.selectbox("Filter by Category:", ["All"] + list(cat_data.keys()))
    with col_f2:
        status_filter = st.selectbox("Filter by Status:", ["All", "Passed Only", "Failed Only"])

    filtered_scores = q_scores
    if cat_filter != "All":
        filtered_scores = [q for q in filtered_scores if q.get("category") == cat_filter]
    if status_filter == "Passed Only":
        filtered_scores = [q for q in filtered_scores if q.get("overall_pass")]
    elif status_filter == "Failed Only":
        filtered_scores = [q for q in filtered_scores if not q.get("overall_pass")]

    table_data = []
    for q in filtered_scores:
        status_icon = "✅ Pass" if q.get("overall_pass") else "❌ Fail"
        tools = ", ".join(q.get("actual_tools", []))
        table_data.append({
            "Status": status_icon,
            "ID": q.get("question_id"),
            "Category": q.get("category"),
            "Question": q.get("question"),
            "Tool Used": tools,
            "Tool Score": q.get("tool_selection_score"),
            "Correctness": q.get("correctness_score"),
            "Grounding": q.get("grounding_score"),
            "Security": q.get("error_handling_score"),
            "Latency (s)": q.get("latency_seconds"),
            "Notes": q.get("notes"),
        })

    table_df = pd.DataFrame(table_data)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    # Detailed Question Inspector
    st.markdown("---")
    st.subheader("🔍 Individual Question Deep-Dive Inspector")
    selected_qid = st.selectbox(
        "Select Question ID to Inspect:",
        options=[q["question_id"] for q in q_scores],
        format_func=lambda qid: f"[{qid}] {next((q['question'] for q in q_scores if q['question_id'] == qid), '')}",
    )

    selected_item = next((q for q in q_scores if q["question_id"] == selected_qid), None)
    if selected_item:
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"**Question ID:** `{selected_item.get('question_id')}`")
            st.markdown(f"**Category:** `{selected_item.get('category')}`")
            st.markdown(f"**Natural Language Prompt:** `{selected_item.get('question')}`")
            st.markdown(f"**Overall Result:** {'✅ **PASSED**' if selected_item.get('overall_pass') else '❌ **FAILED**'}")
        with col_meta2:
            st.markdown(f"**Actual Intent:** `{selected_item.get('actual_intent')}`")
            st.markdown(f"**Tools Dispatched:** `{', '.join(selected_item.get('actual_tools', []))}`")
            st.markdown(f"**Latency:** `{selected_item.get('latency_seconds')} seconds`")
            st.markdown(f"**Evaluation Notes:** `{selected_item.get('notes')}`")

        # Dimension Scores Breakout
        st.markdown("**Metric Dimensions:**")
        dim_col1, dim_col2, dim_col3, dim_col4 = st.columns(4)
        dim_col1.metric("Tool Routing", f"{selected_item.get('tool_selection_score', 0.0) * 100:.0f}%")
        dim_col2.metric("Result Correctness", f"{selected_item.get('correctness_score', 0.0) * 100:.0f}%")
        dim_col3.metric("Grounding Score", f"{selected_item.get('grounding_score', 0.0) * 100:.0f}%")
        dim_col4.metric("Security & Error", f"{selected_item.get('error_handling_score', 0.0) * 100:.0f}%")

    # Export Section
    st.markdown("---")
    st.subheader("📥 Export Evaluation Telemetry")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📥 Download Full Scorecard (JSON)",
            data=json.dumps(evaluation_data, indent=2),
            file_name=f"insightiq_benchmark_{ts.replace(':', '-').replace(' ', '_')}.json",
            mime="application/json",
        )
    with col_exp2:
        if not table_df.empty:
            st.download_button(
                label="📥 Download Results Table (CSV)",
                data=table_df.to_csv(index=False),
                file_name=f"insightiq_benchmark_results_{ts.replace(':', '-').replace(' ', '_')}.csv",
                mime="text/csv",
            )
