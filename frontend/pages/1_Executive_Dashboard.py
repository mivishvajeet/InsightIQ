"""
InsightIQ: Executive KPI Dashboard.
Presents executive-level metrics, revenue growth, and operational health.
"""

import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.kpi_service import KPIService
from frontend.components.styles import apply_theme, metric_card, configure_plotly_theme

st.set_page_config(page_title="Executive Dashboard | InsightIQ", page_icon="📊", layout="wide")
apply_theme()

st.title("📊 Executive KPI Dashboard")
st.markdown("High-level performance summary of completed transactions, customer acquisition, and platform satisfaction.")

# 1. Fetch Executive KPIs
with st.spinner("Loading executive metrics..."):
    kpis = KPIService.get_executive_summary()
    monthly_df = KPIService.get_monthly_growth_trend()

# 2. Headline Metric Cards
st.markdown("<div class='section-header'>Headline Business Performance</div>", unsafe_allow_html=True)
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    metric_card("Total Revenue", f"R$ {kpis['total_revenue']:,.2f}", f"GMV: R$ {kpis['total_gmv']:,.2f}")
with col2:
    metric_card("Delivered Orders", f"{kpis['delivered_orders']:,}", f"Total: {kpis['total_orders']:,}")
with col3:
    metric_card("Avg Order Value", f"R$ {kpis['aov']:.2f}", "Per completed order")
with col4:
    metric_card("Unique Customers", f"{kpis['unique_customers']:,}", "Distinct individuals")
with col5:
    metric_card("Repeat Rate", f"{kpis['repeat_purchase_rate_pct']:.2f}%", f"{kpis['repeat_customers']:,} repeat buyers")
with col6:
    metric_card("Avg Review Score", f"{kpis['avg_review_score']:.2f} ★", f"On-time: {kpis['on_time_rate_pct']:.1f}%")

# 3. Monthly Sales & Orders Trend (Dual-Axis Chart)
st.markdown("<div class='section-header'>Monthly Revenue & Order Volume Growth</div>", unsafe_allow_html=True)

# Filter out zero-months (e.g. post-cutoff 2018-09/10) for cleaner trend visualization
active_months = monthly_df[monthly_df["total_delivered_revenue"] > 0]

fig = go.Figure()
fig.add_trace(
    go.Bar(
        x=active_months["year_month"],
        y=active_months["total_delivered_revenue"],
        name="Delivered Revenue (R$)",
        marker_color="#0D9488",
        opacity=0.85,
    )
)
fig.add_trace(
    go.Scatter(
        x=active_months["year_month"],
        y=active_months["delivered_orders"],
        name="Delivered Orders",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color="#F59E0B", width=3),
        marker=dict(size=6),
    )
)

fig.update_layout(
    yaxis=dict(title="Revenue (BRL R$)", gridcolor="#334155"),
    yaxis2=dict(title="Order Count", overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
)
configure_plotly_theme(fig)
st.plotly_chart(fig, use_container_width=True)

# 4. Period Comparison Data Table
st.markdown("<div class='section-header'>Monthly Performance Breakdown & MoM Changes</div>", unsafe_allow_html=True)
display_cols = [
    "year_month",
    "total_delivered_revenue",
    "revenue_mom_pct",
    "delivered_orders",
    "orders_mom_pct",
    "aov",
    "active_unique_customers",
]
st.dataframe(
    active_months[display_cols].rename(
        columns={
            "year_month": "Month",
            "total_delivered_revenue": "Revenue (R$)",
            "revenue_mom_pct": "Revenue MoM %",
            "delivered_orders": "Orders",
            "orders_mom_pct": "Orders MoM %",
            "aov": "AOV (R$)",
            "active_unique_customers": "Active Customers",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
