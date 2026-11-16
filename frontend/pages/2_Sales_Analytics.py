"""
InsightIQ: Sales Analytics Dashboard.
Detailed category rankings, geographic sales distribution, and order status breakdown.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.database import readonly_engine
from frontend.components.styles import apply_theme, configure_plotly_theme

st.set_page_config(page_title="Sales Analytics | InsightIQ", page_icon="📈", layout="wide")
apply_theme()

st.title("📈 Sales & Category Analytics")
st.markdown("Analyze commercial performance across product categories, Brazilian states, and fulfillment lifecycles.")

# Fetch data from approved views
with readonly_engine.connect() as conn:
    category_df = pd.read_sql("SELECT * FROM analytics.v_category_performance;", conn)
    state_df = pd.read_sql("SELECT * FROM analytics.v_state_sales_distribution;", conn)
    status_df = pd.read_sql(
        """
        SELECT order_status, COUNT(*) AS count, ROUND(COUNT(*)::NUMERIC / 99441.0 * 100, 2) AS pct
        FROM analytics.fact_orders
        GROUP BY order_status
        ORDER BY count DESC;
        """,
        conn
    )

# Section 1: Product Category Performance
st.markdown("<div class='section-header'>Top Product Categories by Revenue</div>", unsafe_allow_html=True)
col_left, col_right = st.columns([3, 2])

with col_left:
    top_categories = category_df.head(10).sort_values("total_revenue", ascending=True)
    fig_cat = px.bar(
        top_categories,
        x="total_revenue",
        y="product_category",
        orientation="h",
        title="Top 10 Product Categories by Revenue (BRL R$)",
        color="total_revenue",
        color_continuous_scale="Teal",
        labels={"total_revenue": "Revenue (R$)", "product_category": "Category"},
    )
    fig_cat.update_layout(coloraxis_showscale=False)
    configure_plotly_theme(fig_cat)
    st.plotly_chart(fig_cat, use_container_width=True)

with col_right:
    fig_status = px.pie(
        status_df,
        names="order_status",
        values="count",
        title="Order Status Breakdown (Platform History)",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Prism,
    )
    configure_plotly_theme(fig_status)
    st.plotly_chart(fig_status, use_container_width=True)

# Section 2: Geographic Distribution (State-level)
st.markdown("<div class='section-header'>Geographic Sales Performance (Brazilian States)</div>", unsafe_allow_html=True)

fig_state = px.bar(
    state_df.head(15),
    x="customer_state",
    y="total_delivered_revenue",
    title="Top 15 States by Delivered Revenue",
    color="total_delivered_revenue",
    color_continuous_scale="Blues",
    labels={"total_delivered_revenue": "Revenue (R$)", "customer_state": "State"},
)
fig_state.update_layout(coloraxis_showscale=False)
configure_plotly_theme(fig_state)
st.plotly_chart(fig_state, use_container_width=True)

# State Metrics Table
st.dataframe(
    state_df.rename(
        columns={
            "customer_state": "State",
            "unique_customers": "Unique Customers",
            "total_orders": "Total Orders",
            "total_delivered_revenue": "Delivered Revenue (R$)",
            "avg_order_value": "AOV (R$)",
            "avg_delivery_lead_time_days": "Avg Lead Time (Days)",
            "on_time_delivery_rate_pct": "On-Time Rate %",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

