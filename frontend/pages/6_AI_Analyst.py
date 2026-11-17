"""
InsightIQ: AI Analyst & Autonomous Agent Studio.
Empowers business users and data analysts to interact with enterprise data using natural language,
orchestrating SQL Analytics, RAG Knowledge Retrieval, and Python Analytics with full execution transparency.
"""

import sys
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.tools.registry import tool_registry
from frontend.components.styles import apply_theme, configure_plotly_theme

st.set_page_config(page_title="AI Analyst | InsightIQ", page_icon="🤖", layout="wide")
apply_theme()

st.title("🤖 AI Analyst & Agent Studio")
st.markdown(
    "Ask natural language business questions. InsightIQ's autonomous agent interprets intent, coordinates specialized tools "
    "(PostgreSQL SQL Analytics, ChromaDB Knowledge RAG, and Python Statistical Engines), and presents evidence-backed answers."
)

# Sidebar Tool Monitor
with st.sidebar:
    st.subheader("🛠️ Registered Agent Tools")
    tools = tool_registry.list_tools()
    for t in tools:
        st.markdown(f"**`{t['name']}`**")
        st.caption(t["description"])
        st.markdown("---")

tab_agent, tab_sql, tab_rag = st.tabs([
    "⚡ Autonomous Agent Orchestrator",
    "📊 Direct SQL Analytics",
    "📚 Direct Knowledge RAG",
])

# =========================================================================
# TAB 1: AUTONOMOUS AGENT ORCHESTRATOR
# =========================================================================
with tab_agent:
    st.subheader("Autonomous Multi-Tool Agent Orchestration")
    st.markdown("The agent automatically determines whether SQL, RAG, Python calculations, or multiple tools are required.")

    AGENT_EXAMPLES = [
        "What is the monthly revenue trend?",
        "Which product category generates the highest sales?",
        "Compare sales performance across Brazilian states",
        "How is customer retention calculated?",
        "What is our delivered revenue and how is it defined?",
        "Are delivery delays associated with lower review scores?",
        "Detect statistical revenue anomalies and spikes",
        "What customer segments generate the most revenue?",
    ]

    col_select, col_mode = st.columns([3, 1])
    with col_select:
        selected_agent_q = st.selectbox("💡 Suggested Business Questions:", ["-- Custom Question --"] + AGENT_EXAMPLES, key="agent_select")
    with col_mode:
        mode_override = st.selectbox("Execution Mode:", ["auto", "sql", "rag", "python", "hybrid"], index=0)

    user_agent_query = st.text_input(
        "Enter your question for the AI Agent:",
        value="" if selected_agent_q.startswith("--") else selected_agent_q,
        key="agent_input",
    )

    if st.button("🚀 Run Agentic Workflow", type="primary", key="btn_agent"):
        if not user_agent_query:
            st.warning("Please enter or select a business question.")
        else:
            with st.spinner("Agent analyzing intent, dispatching tools, and synthesizing evidence..."):
                start_t = time.time()
                result = orchestrator_agent.run(
                    question=user_agent_query,
                    mode_override=None if mode_override == "auto" else mode_override,
                )
                elapsed = round(time.time() - start_t, 2)

            st.success(f"✅ Workflow Completed in {elapsed}s | Intent: **{result.intent.upper()}** | Tools Used: **{', '.join(result.tools_used)}**")

            # Execution Steps Trace
            st.markdown("<div class='section-header'>Agent Execution Trace & Tool Thought Steps</div>", unsafe_allow_html=True)
            for step in result.execution_steps:
                tool_badge = f" [`{step['tool_name']}`]" if step.get("tool_name") else ""
                icon = "🟢" if step["status"] == "completed" else "🔴"
                st.markdown(
                    f"{icon} **Step {step['step_number']}: {step['step_name']}**{tool_badge} "
                    f"({step['duration_seconds']}s) — *{step['description']}*"
                )

            # Executive Answer
            st.markdown("<div class='section-header'>Executive Business Answer</div>", unsafe_allow_html=True)
            st.markdown(result.final_answer)

            # Structured Data & Visual Evidence (if SQL or Python data present)
            if result.data_table:
                df_data = pd.DataFrame(result.data_table)
                st.markdown("<div class='section-header'>Structured Data Evidence</div>", unsafe_allow_html=True)
                st.dataframe(df_data, use_container_width=True, hide_index=True)

                num_cols = df_data.select_dtypes(include=["number"]).columns
                if len(num_cols) > 0 and len(df_data.columns) > 1:
                    st.markdown("<div class='section-header'>Visual Evidence</div>", unsafe_allow_html=True)
                    x_col = df_data.columns[0]
                    y_col = num_cols[0]
                    fig = px.bar(df_data.head(15), x=x_col, y=y_col, title=f"{y_col} by {x_col}", color_discrete_sequence=["#0D9488"])
                    configure_plotly_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)

            # SQL Query Transparency (if SQL tool was used)
            if result.sql_query:
                st.markdown("<div class='section-header'>Generated PostgreSQL Query</div>", unsafe_allow_html=True)
                st.code(result.sql_query, language="sql")

            # Citations (if RAG tool was used)
            if result.citations:
                st.markdown("<div class='section-header'>Retrieved Knowledge Base Citations</div>", unsafe_allow_html=True)
                for i, c in enumerate(result.citations, 1):
                    with st.expander(f"📄 Citation [{i}]: {c['source']} — {c['section']}"):
                        st.markdown(f"**Chunk ID:** `{c['chunk_id']}`")
                        st.markdown(f"**Relevance:** `{c['relevance_score']:.4f}`")
                        st.info(c["snippet"])

# =========================================================================
# TAB 2: DIRECT SQL ANALYTICS
# =========================================================================
with tab_sql:
    st.subheader("Direct Natural Language SQL Execution")
    st.markdown("Translates natural-language questions directly to PostgreSQL with AST security checks.")

    sql_q = st.text_input("Enter SQL-specific analytical question:", key="direct_sql_input", value="What is the average order value?")
    if st.button("Run SQL", key="btn_direct_sql"):
        with st.spinner("Generating SQL..."):
            out = tool_registry.execute_tool("sql_analytics_tool", question=sql_q)
        if out["success"]:
            st.success(f"Executed in {out['execution_time_seconds']}s ({out['row_count']} rows)")
            st.code(out["sql"], language="sql")
            st.dataframe(pd.DataFrame(out["data"]), use_container_width=True)
        else:
            st.error(out["error"])

# =========================================================================
# TAB 3: DIRECT KNOWLEDGE RAG
# =========================================================================
with tab_rag:
    st.subheader("Direct Knowledge Base Semantic Search")
    st.markdown("Queries ChromaDB vector documentation directly.")

    rag_q = st.text_input("Enter domain question:", key="direct_rag_input", value="How is customer retention calculated?")
    if st.button("Search Knowledge Base", key="btn_direct_rag"):
        with st.spinner("Retrieving from ChromaDB..."):
            out = tool_registry.execute_tool("rag_retrieval_tool", query=rag_q, top_k=3, synthesize_answer=True)
        if out["success"]:
            st.success(f"Completed in {out['execution_time_seconds']}s")
            st.markdown(out["answer"])
            for c in out["citations"]:
                st.caption(f"Source: `{c['source']}` — {c['section']}")
        else:
            st.error(out["error"])
