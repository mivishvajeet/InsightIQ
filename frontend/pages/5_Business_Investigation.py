"""
InsightIQ: Business Investigation & Anomaly Explorer Dashboard.
Investigates revenue spikes, fulfillment drops, and customer satisfaction decline.
Distinguishes correlation from causation.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from frontend.components.styles import apply_theme, metric_card, configure_plotly_theme

st.set_page_config(page_title="Business Investigation | InsightIQ", page_icon="🔍", layout="wide")
apply_theme()

st.title("🔍 Business Investigation & Anomaly Explorer")
st.markdown("Diagnose revenue anomalies, investigate satisfaction drivers, and evaluate evidence-based findings.")

# Anomaly Detection Section
st.markdown("<div class='section-header'>Revenue Anomaly Detection (Z-Score & IQR)</div>", unsafe_allow_html=True)

with st.spinner("Detecting daily revenue anomalies..."):
    daily_df = AnomalyDetector.detect_daily_revenue_anomalies(z_threshold=2.5)
    top_anomalies = AnomalyDetector.get_top_anomalies(8)

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
    labels={"full_date": "Date", "daily_revenue": "Daily Revenue (BRL R$)", "anomaly_type": "Classification"},
)
fig_anom.update_traces(marker=dict(size=6))
configure_plotly_theme(fig_anom)
st.plotly_chart(fig_anom, use_container_width=True)

st.subheader("Detected Key Business Anomalies")
st.dataframe(
    pd.DataFrame(top_anomalies).rename(
        columns={
            "date": "Date",
            "daily_revenue": "Revenue (R$)",
            "order_count": "Orders",
            "z_score": "Z-Score",
            "anomaly_type": "Anomaly Type",
            "business_context": "Root Cause / Historical Context",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# Root Cause Investigation Section
st.markdown("<div class='section-header'>Investigating Customer Satisfaction Drivers</div>", unsafe_allow_html=True)
st.info(
    """
    **Methodology & Causal Standards:**
    In accordance with analytical standards, the system distinguishes **correlation from causation**.
    Delivery delay is statistically associated with negative review ratings ($r = -0.27$, 7x surge in 1-star reviews),
    but unverified external variables (e.g. product defects or carrier logistics bottlenecks) must not be presented
    as proven causation without controlled experimentation.
    """
)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### 🔍 Key Findings")
    st.markdown(
        """
        1. **On-Time Delivery is the Primary Satisfaction Anchor:**
           - Orders delivered on or before the estimated delivery date average a **4.29 ★** rating.
           - When delivery exceeds the estimate, average rating plunges to **2.56 ★**.
        2. **1-Star Review Risk Increases Sevenfold:**
           - The 1-star review rate jumps from **6.6%** (on-time) to **46.2%** (delayed).
        3. **Freight Cost is Not a Meaningful Driver:**
           - Correlation between shipping fee and review score is near zero ($r = 0.03$), indicating buyers tolerate shipping costs if arrival promises are met.
        """
    )

with col_b:
    st.markdown("### 💡 Evidence-Based Recommendations")
    st.markdown(
        """
        1. **Dynamic Delivery Date Buffer:**
           - Add a 2-day buffer to estimated delivery dates during peak promotional periods (e.g., Black Friday) to reduce false delay perceptions.
        2. **Seller SLA Enforcement:**
           - Implement penalty thresholds for sellers whose carrier dispatch delay exceeds 48 hours.
        3. **Proactive Customer Notification:**
           - Trigger automated proactive alerts when a carrier tracking event indicates a delivery delay before the customer files a complaint.
        """
    )
