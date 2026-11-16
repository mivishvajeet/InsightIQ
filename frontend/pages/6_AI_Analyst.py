"""
InsightIQ: AI Analyst & Natural Language Query Interface.
Enables natural-language questions, SQL execution transparency, and contextual RAG answers.
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
from frontend.components.styles import apply_theme, configure_plotly_theme

st.set_page_config(page_title="AI Analyst | InsightIQ", page_icon="🤖", layout="wide")
apply_theme()

st.title("🤖 AI Analyst & Natural Language SQL")
st.markdown("Ask natural language business questions. The local **Qwen 2.5 3B** LLM understands the schema, generates validated SQL, and queries PostgreSQL in real-time.")

sql_generator = SQLGenerator()

# Sample suggested questions
SUGGESTED_QUESTIONS = [
    "What is the monthly revenue trend?",
    "Which product category generates the highest sales?",
    "Compare sales performance across Brazilian states",
    "How many customers made repeat purchases?",
    "What is the average order value?",
    "Are delivery delays associated with lower review scores?",
    "Which sellers have the highest cancellation rates?",
]

selected_prompt = st.selectbox("💡 Choose an example business question or type below:", ["-- Custom Question --"] + SUGGESTED_QUESTIONS)

user_query = st.text_input("Enter your business question:", value="" if selected_prompt.startswith("--") else selected_prompt)

if st.button("🚀 Analyze with Agent", type="primary"):
    if not user_query:
        st.warning("Please enter or select a business question.")
    else:
        with st.spinner("Qwen 2.5 3B interpreting question, generating SQL, and querying PostgreSQL..."):
            start_t = time.time()
            sql, df_res, error = sql_generator.generate_and_execute(user_query)
            explanation = sql_generator.explain_query(user_query, sql) if not error else "Execution error occurred."
            elapsed = round(time.time() - start_t, 2)

        if error:
            st.error(f"❌ Execution Error: {error}")
            st.code(sql, language="sql")
        else:
            st.success(f"✅ Analysis Complete ({len(df_res)} rows returned in {elapsed}s)")

            # Display Reasoning & SQL Transparency
            st.markdown("<div class='section-header'>Agent Reasoning & SQL Transparency</div>", unsafe_allow_html=True)
            st.markdown(f"**Explanation:** {explanation}")
            st.code(sql.strip(), language="sql")

            # Display Supporting Table
            st.markdown("<div class='section-header'>Structured Query Results</div>", unsafe_allow_html=True)
            st.dataframe(df_res, use_container_width=True, hide_index=True)

            # Dynamic Chart if numerical columns exist
            num_cols = df_res.select_dtypes(include=["number"]).columns
            if len(num_cols) > 0 and len(df_res.columns) > 1:
                st.markdown("<div class='section-header'>Visual Evidence</div>", unsafe_allow_html=True)
                x_col = df_res.columns[0]
                y_col = num_cols[0]
                fig = px.bar(df_res.head(15), x=x_col, y=y_col, title=f"{y_col} by {x_col}", color_discrete_sequence=["#0D9488"])
                configure_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
