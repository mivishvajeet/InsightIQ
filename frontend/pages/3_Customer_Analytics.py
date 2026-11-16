"""
InsightIQ: Customer Analytics & Segmentation Dashboard.
RFM (Recency, Frequency, Monetary) segmentation, repeat purchase analysis, and high-value customer profiles.
"""

import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.customer_analytics import CustomerAnalyticsService
from frontend.components.styles import apply_theme, metric_card, configure_plotly_theme

st.set_page_config(page_title="Customer Analytics | InsightIQ", page_icon="👥", layout="wide")
apply_theme()

st.title("👥 Customer Analytics & RFM Segmentation")
st.markdown("Analyze customer purchasing behavior, value concentration, and repeat buying loyalty.")

with st.spinner("Loading customer metrics..."):
    rfm_df = CustomerAnalyticsService.get_rfm_summary()
    top_customers = CustomerAnalyticsService.get_top_customers(15)

# Section 1: Customer Segmentation Overview
st.markdown("<div class='section-header'>RFM Customer Segmentation</div>", unsafe_allow_html=True)
col_l, col_r = st.columns([1, 1])

with col_l:
    fig_cust = px.bar(
        rfm_df,
        x="customer_segment",
        y="customer_count",
        title="Customer Count by RFM Segment",
        color="customer_segment",
        color_discrete_sequence=px.colors.qualitative.Bold,
        text="customer_count",
    )
    fig_cust.update_traces(textposition="outside")
    fig_cust.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Customers")
    configure_plotly_theme(fig_cust)
    st.plotly_chart(fig_cust, use_container_width=True)

with col_r:
    fig_rev = px.pie(
        rfm_df,
        names="customer_segment",
        values="total_revenue",
        title="Revenue Contribution by Customer Segment",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    configure_plotly_theme(fig_rev)
    st.plotly_chart(fig_rev, use_container_width=True)

# Segment Summary Table
st.dataframe(
    rfm_df.rename(
        columns={
            "customer_segment": "Segment",
            "customer_count": "Customers",
            "customer_pct": "% of Customers",
            "total_revenue": "Total Revenue (R$)",
            "revenue_pct": "% of Revenue",
            "avg_monetary": "Avg Spend (R$)",
            "avg_frequency": "Avg Orders",
            "avg_recency_days": "Avg Recency (Days)",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# Section 2: Top High-Value Customers (LTV)
st.markdown("<div class='section-header'>Top 15 Highest-Value Customer Accounts</div>", unsafe_allow_html=True)
st.dataframe(
    top_customers.rename(
        columns={
            "customer_unique_id": "Customer Unique ID",
            "city": "City",
            "state": "State",
            "order_count": "Orders Placed",
            "total_spend": "Total Spend (R$)",
            "avg_order_value": "Avg Order Value (R$)",
            "avg_review_score": "Avg Review Score",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
