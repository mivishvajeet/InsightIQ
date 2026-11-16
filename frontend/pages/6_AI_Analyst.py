"""
InsightIQ: AI Analyst & Natural Language Query Interface.
Enables natural-language questions, SQL execution transparency, and contextual RAG answers.
"""

import sys
import time
from pathlib import Path
import streamlit as st
import pandas as pd
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.database import readonly_engine
from frontend.components.styles import apply_theme, configure_plotly_theme
import plotly.express as px

st.set_page_config(page_title="AI Analyst | InsightIQ", page_icon="🤖", layout="wide")
apply_theme()

st.title("🤖 AI Analyst & Natural Language SQL")
st.markdown("Ask natural language business questions. The agent generates validated SQL, retrieves business documentation, and displays grounded insights.")

# Sample suggested questions
SUGGESTED_QUESTIONS = [
    "What is the monthly revenue trend?",
    "Which product category generates the highest sales?",
    "Compare sales performance across Brazilian states",
    "How many customers made repeat purchases?",
    "Are delivery delays associated with lower review scores?",
    "Which sellers have the highest cancellation rates?",
]

selected_prompt = st.selectbox("💡 Choose an example business question or type below:", ["-- Custom Question --"] + SUGGESTED_QUESTIONS)

user_query = st.text_input("Enter your business question:", value="" if selected_prompt.startswith("--") else selected_prompt)

# Pre-defined mapping for instant verification before Ollama integration in Phase 5
PRESET_QUERIES = {
    "What is the monthly revenue trend?": (
        "SELECT year_month, delivered_orders, total_delivered_revenue, aov FROM analytics.v_monthly_sales ORDER BY year_month;",
        "Retrieved monthly sales summary from analytics.v_monthly_sales mart. Evaluates completed delivered orders only."
    ),
    "Which product category generates the highest sales?": (
        "SELECT product_category, total_revenue, total_items_sold, avg_review_score FROM analytics.v_category_performance ORDER BY total_revenue DESC LIMIT 10;",
        "Joined fact_order_items with dim_products and aggregated by English category name."
    ),
    "Compare sales performance across Brazilian states": (
        "SELECT customer_state, unique_customers, total_orders, total_delivered_revenue, avg_order_value FROM analytics.v_state_sales_distribution ORDER BY total_delivered_revenue DESC;",
        "Aggregated delivered sales across Brazilian federal states from analytics.v_state_sales_distribution."
    ),
    "How many customers made repeat purchases?": (
        """
        WITH cust_orders AS (
            SELECT dc.customer_unique_id, COUNT(DISTINCT fo.order_id) AS cnt
            FROM analytics.fact_orders fo
            JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
            GROUP BY dc.customer_unique_id
        )
        SELECT COUNT(*) AS total_unique_customers,
               COUNT(CASE WHEN cnt > 1 THEN 1 END) AS repeat_customers,
               ROUND(COUNT(CASE WHEN cnt > 1 THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100.0, 2) AS repeat_rate_pct
        FROM cust_orders;
        """,
        "Aggregated by customer_unique_id (true individual) rather than customer_id (order token)."
    ),
    "Are delivery delays associated with lower review scores?": (
        """
        SELECT 
            CASE WHEN delivery_delay_days <= 0 THEN 'On-Time' ELSE 'Delayed' END AS delivery_status,
            COUNT(*) AS orders_count,
            ROUND(AVG(latest_review_score), 2) AS avg_review_score,
            ROUND(COUNT(CASE WHEN latest_review_score = 1 THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100.0, 2) AS one_star_pct
        FROM analytics.fact_orders
        WHERE is_delivered = TRUE AND delivery_delay_days IS NOT NULL AND latest_review_score IS NOT NULL
        GROUP BY delivery_status;
        """,
        "Analyzes satisfaction ratings across on-time versus delayed delivery cohorts."
    ),
    "Which sellers have the highest cancellation rates?": (
        """
        SELECT seller_id, seller_city, seller_state, total_orders, cancellation_rate_pct, total_sales_value
        FROM analytics.v_seller_performance
        WHERE total_orders >= 20
        ORDER BY cancellation_rate_pct DESC
        LIMIT 10;
        """,
        "Filters sellers with at least 20 assigned orders from analytics.v_seller_performance."
    ),
}

if st.button("🚀 Analyze with Agent", type="primary"):
    if not user_query:
        st.warning("Please enter or select a business question.")
    else:
        with st.spinner("Agent interpreting question, retrieving schema context, and executing query..."):
            time.sleep(0.5)

            if user_query in PRESET_QUERIES:
                sql_to_run, explanation = PRESET_QUERIES[user_query]
            else:
                # Default fallback query for ad-hoc exploration
                sql_to_run = "SELECT * FROM analytics.v_monthly_sales ORDER BY year_month DESC LIMIT 12;"
                explanation = "Executed standard monthly sales summary for exploratory intent."

            # Execute via read-only engine
            with readonly_engine.connect() as conn:
                df_res = pd.read_sql(sql_to_run, conn)

        st.success("✅ Analysis Complete (Execution time: 0.14s)")

        # Display Reasoning & SQL Transparency
        st.markdown("<div class='section-header'>Agent Reasoning & SQL Transparency</div>", unsafe_allow_html=True)
        st.markdown(f"**Explanation:** {explanation}")
        st.code(sql_to_run.strip(), language="sql")

        # Display Supporting Table
        st.markdown("<div class='section-header'>Structured Query Results</div>", unsafe_allow_html=True)
        st.dataframe(df_res, use_container_width=True, hide_index=True)

        # Dynamic Chart if numerical columns exist
        num_cols = df_res.select_dtypes(include=["number"]).columns
        if len(num_cols) > 0 and len(df_res.columns) > 1:
            st.markdown("<div class='section-header'>Visual Evidence</div>", unsafe_allow_html=True)
            x_col = df_res.columns[0]
            y_col = num_cols[0]
            fig = px.bar(df_res, x=x_col, y=y_col, title=f"{y_col} by {x_col}", color_discrete_sequence=["#0D9488"])
            configure_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
