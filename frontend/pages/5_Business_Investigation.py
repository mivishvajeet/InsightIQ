"""
InsightIQ: Business Investigation Suite.
Interactive deep-dive root cause analysis:
1. Revenue change variance decomposition (Volume Effect vs AOV Effect)
2. Customer satisfaction degradation and delay thresholds
3. Seller cancellation risk and operational bottlenecks
4. Underperforming merchandise categories
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.investigation.revenue_investigator import RevenueAnomalyInvestigator
from backend.app.investigation.satisfaction_investigator import SatisfactionDriverInvestigator
from backend.app.investigation.operational_investigator import OperationalBottleneckInvestigator
from backend.app.investigation.category_investigator import CategoryPerformanceInvestigator
from backend.app.services.anomaly_detector import AnomalyDetector
from frontend.components.styles import apply_theme, configure_plotly_theme

st.set_page_config(page_title="Business Investigation | InsightIQ", page_icon="🔍", layout="wide")
apply_theme()

st.title("🔍 Business Investigation & Root Cause Studio")
st.markdown(
    "Perform evidence-based root cause investigations into revenue contractions, customer satisfaction drivers, "
    "operational friction, and category health. Enforces strict correlation-vs-causation guardrails."
)

tab_rev, tab_sat, tab_ops, tab_cat = st.tabs([
    "📈 Revenue Variance Decomposition",
    "⭐ Satisfaction & Delay Cliffs",
    "🚚 Seller & Transit Bottlenecks",
    "📦 Underperforming Categories",
])

# =========================================================================
# TAB 1: REVENUE VARIANCE DECOMPOSITION
# =========================================================================
with tab_rev:
    st.subheader("Period-over-Period Revenue Decomposition (Volume vs Price Effect)")
    st.markdown("Decompose month-over-month revenue shifts into **Volume Effect** ($\Delta Orders \times AOV_{prior}$) and **Price Effect** ($\Delta AOV \times Orders_{curr}$).")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        curr_m = st.selectbox("Current Period:", ["2018-04", "2018-05", "2018-03", "2018-02", "2018-01", "2017-11"], index=0)
    with col2:
        prior_m = st.selectbox("Prior Period:", ["2018-03", "2018-04", "2018-02", "2018-01", "2017-10"], index=0)

    if st.button("Analyze Period Variance", type="primary", key="btn_rev_var"):
        with st.spinner("Decomposing revenue shift..."):
            res = RevenueAnomalyInvestigator.investigate_period_change(curr_m, prior_m)

        if "error" in res:
            st.error(res["error"])
        else:
            st.success(res["executive_takeaway"])

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Delta Revenue", f"R$ {res['delta_revenue']:,.2f}", f"{res['pct_change']:+,.2f}%")
            kpi2.metric("Volume Effect", f"R$ {res['volume_effect']:,.2f}")
            kpi3.metric("Price / AOV Effect", f"R$ {res['price_effect']:,.2f}")
            kpi4.metric("Primary Driver", res["primary_driver"].title())

            col_g, col_d = st.columns(2)
            with col_g:
                st.markdown("#### 🚀 Top Growing Categories")
                st.dataframe(pd.DataFrame(res["top_growth_categories"]), use_container_width=True, hide_index=True)
            with col_d:
                st.markdown("#### 🔻 Top Dragging Categories")
                st.dataframe(pd.DataFrame(res["top_drag_categories"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Daily Revenue Anomaly Timeline")
    daily_df = AnomalyDetector.detect_daily_revenue_anomalies(z_threshold=2.5)
    fig_anom = px.scatter(
        daily_df,
        x="full_date",
        y="daily_revenue",
        color="anomaly_type",
        color_discrete_map={
            "Normal": "#64748B",
            "Revenue Spike (Surge)": "#10B981",
            "Revenue Drop (Dip)": "#EF4444",
        },
        title="Daily Revenue Trend with Statistical Anomaly Highlights",
    )
    configure_plotly_theme(fig_anom)
    st.plotly_chart(fig_anom, use_container_width=True)

# =========================================================================
# TAB 2: SATISFACTION & DELAY CLIFFS
# =========================================================================
with tab_sat:
    st.subheader("Customer Satisfaction Drivers & The 3-Day Delay Cliff")
    sat_res = SatisfactionDriverInvestigator.investigate_satisfaction_drivers()

    st.info(f"🛡️ **Causal Guardrail:** {sat_res['causation_guardrail']}")
    st.success(sat_res["executive_summary"])

    df_tiers = pd.DataFrame(sat_res["delay_tiers"])
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        fig_score = px.bar(
            df_tiers,
            x="delay_tier",
            y="avg_score",
            color="avg_score",
            color_continuous_scale="Teal",
            title="Mean Review Score by Delay Tier",
            labels={"delay_tier": "Delay Tier", "avg_score": "Average Rating (★)"},
        )
        configure_plotly_theme(fig_score)
        st.plotly_chart(fig_score, use_container_width=True)

    with col_t2:
        fig_1star = px.bar(
            df_tiers,
            x="delay_tier",
            y="one_star_pct",
            color="one_star_pct",
            color_continuous_scale="Reds",
            title="1-Star Review Risk Percentage by Delay Tier",
            labels={"delay_tier": "Delay Tier", "one_star_pct": "1-Star Risk (%)"},
        )
        configure_plotly_theme(fig_1star)
        st.plotly_chart(fig_1star, use_container_width=True)

    st.markdown("#### Geographic Satisfaction & Logistics Performance across Top 10 States")
    st.dataframe(pd.DataFrame(sat_res["geographic_logistics"]), use_container_width=True, hide_index=True)

# =========================================================================
# TAB 3: SELLER & TRANSIT BOTTLENECKS
# =========================================================================
with tab_ops:
    st.subheader("Problematic Sellers & Logistics Transit Bottlenecks")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### 🚨 High-Cancellation Sellers")
        sellers_res = OperationalBottleneckInvestigator.investigate_problematic_sellers(min_orders=15, top_n=8)
        st.caption(sellers_res["executive_summary"])
        st.dataframe(pd.DataFrame(sellers_res["sellers"]), use_container_width=True, hide_index=True)

    with col_s2:
        st.markdown("#### 🛣️ Slowest Inter-State Shipping Corridors")
        transit_res = OperationalBottleneckInvestigator.investigate_transit_bottlenecks(min_orders=30, top_n=8)
        st.caption(transit_res["executive_summary"])
        st.dataframe(pd.DataFrame(transit_res["corridors"]), use_container_width=True, hide_index=True)

# =========================================================================
# TAB 4: UNDERPERFORMING CATEGORIES
# =========================================================================
with tab_cat:
    st.subheader("Merchandise Categories with Lowest Satisfaction & High Freight Drag")
    cat_res = CategoryPerformanceInvestigator.investigate_underperforming_categories(min_items_sold=30, top_n=10)
    st.success(cat_res["executive_summary"])

    df_cat_under = pd.DataFrame(cat_res["underperforming_categories"])
    st.dataframe(df_cat_under, use_container_width=True, hide_index=True)

    fig_cat = px.scatter(
        df_cat_under,
        x="freight_to_price_pct",
        y="avg_review_score",
        size="total_orders",
        color="category",
        title="Freight Cost Burden vs Customer Review Score by Category",
        labels={"freight_to_price_pct": "Freight to Price Ratio (%)", "avg_review_score": "Review Score (★)"},
    )
    configure_plotly_theme(fig_cat)
    st.plotly_chart(fig_cat, use_container_width=True)
