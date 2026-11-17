"""
InsightIQ: AI Analyst & Dual-Mode Agentic Interface.
Supports:
1. Natural Language SQL Analytics (PostgreSQL + AstValidator + Self-Healing)
2. Domain Knowledge Retrieval (LangChain + ChromaDB + Nomic Embed Text + Qwen 2.5 3B)
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

from backend.app.services.sql_generator import SQLGenerator
from backend.app.rag.pipeline import rag_pipeline
from frontend.components.styles import apply_theme, configure_plotly_theme

st.set_page_config(page_title="AI Analyst | InsightIQ", page_icon="🤖", layout="wide")
apply_theme()

st.title("🤖 AI Analyst & Knowledge Agent")
st.markdown(
    "Explore business data through natural language. InsightIQ leverages local **Qwen 2.5 3B** and "
    "**Nomic Embed Text** to generate validated PostgreSQL queries and retrieve grounded business knowledge."
)

tab_sql, tab_rag = st.tabs(["📊 Natural Language SQL", "📚 Knowledge Base RAG"])

sql_generator = SQLGenerator()

# =========================================================================
# TAB 1: NATURAL LANGUAGE SQL
# =========================================================================
with tab_sql:
    st.subheader("Data Analytics & Natural Language SQL")
    st.markdown("Ask quantitative business questions to query PostgreSQL `analytics` schema with automatic AST validation and self-healing.")

    SQL_EXAMPLES = [
        "What is the monthly revenue trend?",
        "Which product category generates the highest sales?",
        "Compare sales performance across Brazilian states",
        "How many customers made repeat purchases?",
        "What is the average order value?",
        "Are delivery delays associated with lower review scores?",
        "Which sellers have the highest cancellation rates?",
    ]

    selected_sql = st.selectbox("💡 Example SQL Questions:", ["-- Custom Query --"] + SQL_EXAMPLES, key="sql_select")
    user_sql_query = st.text_input(
        "Enter your analytical question:",
        value="" if selected_sql.startswith("--") else selected_sql,
        key="sql_input",
    )

    if st.button("🚀 Run SQL Agent", type="primary", key="btn_sql"):
        if not user_sql_query:
            st.warning("Please enter or select a question.")
        else:
            with st.spinner("Qwen 2.5 3B interpreting question, validating SQL AST, and executing against PostgreSQL..."):
                start_t = time.time()
                sql, df_res, error = sql_generator.generate_and_execute(user_sql_query)
                explanation = sql_generator.explain_query(user_sql_query, sql) if not error else "Execution error occurred."
                elapsed = round(time.time() - start_t, 2)

            if error:
                st.error(f"❌ Execution Error: {error}")
                st.code(sql, language="sql")
            else:
                st.success(f"✅ Executed Successfully ({len(df_res)} rows returned in {elapsed}s)")

                st.markdown("<div class='section-header'>Agent Reasoning & SQL Transparency</div>", unsafe_allow_html=True)
                st.markdown(f"**Explanation:** {explanation}")
                st.code(sql.strip(), language="sql")

                st.markdown("<div class='section-header'>Query Results</div>", unsafe_allow_html=True)
                st.dataframe(df_res, use_container_width=True, hide_index=True)

                num_cols = df_res.select_dtypes(include=["number"]).columns
                if len(num_cols) > 0 and len(df_res.columns) > 1:
                    st.markdown("<div class='section-header'>Visual Evidence</div>", unsafe_allow_html=True)
                    x_col = df_res.columns[0]
                    y_col = num_cols[0]
                    fig = px.bar(df_res.head(15), x=x_col, y=y_col, title=f"{y_col} by {x_col}", color_discrete_sequence=["#0D9488"])
                    configure_plotly_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)

# =========================================================================
# TAB 2: KNOWLEDGE BASE RAG
# =========================================================================
with tab_rag:
    st.subheader("Context-Grounded Knowledge Retrieval")
    st.markdown(
        "Query enterprise business rules, metric definitions, database schemas, and delivery policies. "
        "Every response is strictly grounded in the local **ChromaDB** vector store with citation attribution."
    )

    # Status indicator
    rag_status = rag_pipeline.get_status()
    total_vectors = rag_status["vector_store"]["total_chunks"]
    st.info(f"📚 Vector Knowledge Base: **{total_vectors} chunks** indexed in ChromaDB using **nomic-embed-text**.")

    RAG_EXAMPLES = [
        "How is customer retention calculated?",
        "What is the definition of average order value?",
        "Explain the database schema and star model",
        "What does a delivered order mean in this project?",
        "What are the delivery lead time policies and SLAs?",
        "How do delivery delays impact customer review scores?",
    ]

    selected_rag = st.selectbox("💡 Example Knowledge Questions:", ["-- Custom Question --"] + RAG_EXAMPLES, key="rag_select")
    user_rag_query = st.text_input(
        "Enter your knowledge or policy question:",
        value="" if selected_rag.startswith("--") else selected_rag,
        key="rag_input",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        top_k = st.slider("Citations (Top K):", min_value=1, max_value=6, value=4)

    if st.button("🔍 Search Knowledge Base", type="primary", key="btn_rag"):
        if not user_rag_query:
            st.warning("Please enter or select a question.")
        else:
            with st.spinner("Retrieving semantic vectors and synthesizing grounded answer with Qwen 2.5 3B..."):
                start_t = time.time()
                grounded_ans = rag_pipeline.answer_question(user_rag_query, top_k=top_k)
                elapsed = round(time.time() - start_t, 2)

            st.success(f"✅ Grounded Synthesis Complete in {elapsed}s")

            # Answer Card
            st.markdown("<div class='section-header'>Grounded Answer</div>", unsafe_allow_html=True)
            st.markdown(grounded_ans.answer)

            if grounded_ans.has_limitation:
                st.warning("⚠️ **Limitation Notice:** The system detected that the available documentation has limited information regarding this query.")

            # Citations and Context
            st.markdown("<div class='section-header'>Verified Sources & Citations</div>", unsafe_allow_html=True)
            for i, citation in enumerate(grounded_ans.citations, 1):
                pct = int(citation.relevance_score * 100)
                with st.expander(f"📄 Citation [{i}]: {citation.source} — {citation.section} ({pct}% similarity)"):
                    st.markdown(f"**Document Title:** {citation.title}")
                    st.markdown(f"**Chunk ID:** `{citation.chunk_id}`")
                    st.markdown(f"**Relevance Score:** `{citation.relevance_score:.4f}`")
                    st.markdown("**Context Excerpt:**")
                    st.info(citation.snippet)
