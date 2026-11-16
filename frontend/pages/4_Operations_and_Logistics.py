"""
InsightIQ: Operations & Logistics Performance Dashboard.
Delivery delay analysis, correlation with customer satisfaction, and seller performance.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.database import readonly_engine
from frontend.components.styles import apply_theme, metric_card, configure_plotly_theme

st.set_page_config(page_title="Operations & Logistics | InsightIQ", page_icon="🚚", layout="wide")
apply_theme()

st.title("🚚 Operations & Logistics Analytics")
st.markdown("Examine delivery transit lead times, delay distributions, and the direct correlation with customer satisfaction.")

# Run correlation analysis
with st.spinner("Analyzing operational correlations..."):
    analysis = CorrelationAnalyzer.analyze_delivery_vs_satisfaction()

cohorts = analysis["comparative_cohorts"]

# Section 1: Headline Operational Metrics
st.markdown("<div class='section-header'>Delivery Performance & Satisfaction Impact</div>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("On-Time Orders", f"{cohorts['on_time_orders']['count']:,}", f"Avg Rating: {cohorts['on_time_orders']['avg_review_score']} ★")
with col2:
    metric_card("Delayed Orders", f"{cohorts['delayed_orders']['count']:,}", f"Avg Rating: {cohorts['delayed_orders']['avg_review_score']} ★")
with col3:
    metric_card("Satisfaction Drop", f"-{cohorts['satisfaction_drop']} ★", "On-time vs Delayed")
with col4:
    metric_card("1-Star Review Surge", f"{cohorts['one_star_surge_factor']}x", "Higher risk for delayed orders")

# Section 2: Delay Brackets vs Review Scores
st.markdown("<div class='section-header'>Customer Satisfaction by Delay Severity Bracket</div>", unsafe_allow_html=True)

bracket_df = pd.DataFrame(analysis["delay_brackets"])

fig_bar = px.bar(
    bracket_df,
    x="bracket",
    y="avg_review_score",
    color="avg_review_score",
    color_continuous_scale="RdYlGn",
    title="Average Review Score by Delivery Delay Severity",
    text="avg_review_score",
    labels={"bracket": "Delay Category", "avg_review_score": "Average Rating (1-5)"},
)
fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(yaxis_range=[1, 5], coloraxis_showscale=False)
configure_plotly_theme(fig_bar)
st.plotly_chart(fig_bar, use_container_width=True)

# Delay Brackets Table
st.dataframe(
    bracket_df.rename(
        columns={
            "bracket": "Delay Severity Bracket",
            "orders_count": "Orders Count",
            "avg_review_score": "Avg Review Score (1-5)",
            "one_star_pct": "% 1-Star Ratings",
            "five_star_pct": "% 5-Star Ratings",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# Section 3: Seller Cancellation Rates
st.markdown("<div class='section-header'>Top Sellers by Cancellation Rate (Min. 20 Orders)</div>", unsafe_allow_html=True)
with readonly_engine.connect() as conn:
    seller_query = text(
        """
        SELECT
            seller_id,
            seller_city,
            seller_state,
            total_orders,
            cancellation_rate_pct,
            total_sales_value,
            avg_review_score
        FROM analytics.v_seller_performance
        WHERE total_orders >= 20
        ORDER BY cancellation_rate_pct DESC
        LIMIT 10;
        """
    )
    seller_df = pd.read_sql(seller_query, conn)

st.dataframe(
    seller_df.rename(
        columns={
            "seller_id": "Seller ID",
            "seller_city": "City",
            "seller_state": "State",
            "total_orders": "Total Orders",
            "cancellation_rate_pct": "Cancellation Rate %",
            "total_sales_value": "Sales Value (R$)",
            "avg_review_score": "Avg Review Score",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

