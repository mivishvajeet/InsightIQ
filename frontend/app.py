"""
InsightIQ: Agentic Business Intelligence Platform
Main Streamlit Application Entrypoint.
"""

import sys
from pathlib import Path
import streamlit as st

# Setup system path to find backend services
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from frontend.components.styles import apply_theme

# Page Configuration
st.set_page_config(
    page_title="InsightIQ | AI Business Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

st.sidebar.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
st.sidebar.title("InsightIQ")
st.sidebar.caption("Agentic BI & Natural Language Analytics")
st.sidebar.markdown("---")

st.sidebar.info(
    """
    **Platform Architecture:**
    - **Engine:** PostgreSQL 16 (Raw, Staging, Marts)
    - **Analytics:** Python, Pandas, SciPy
    - **AI Agent:** Ollama Qwen 2.5 3B (Local)
    - **RAG:** ChromaDB + Nomic Embed Text
    """
)

# Main Landing Page Content
st.title("⚡ InsightIQ: Agentic Business Intelligence Platform")
st.markdown(
    """
    Welcome to **InsightIQ**, an AI-powered Business Intelligence platform designed to interact with
    enterprise e-commerce data using natural language, contextual RAG documentation, and validated SQL execution.
    
    ### Explore Modules:
    - 📊 **Executive Dashboard:** High-level platform KPIs (Revenue, Orders, AOV, Satisfaction).
    - 📈 **Sales Analytics:** Monthly revenue trends, category performance, and geographic breakdown.
    - 👥 **Customer Analytics:** RFM segmentation, cohort retention, and repeat buyer behavior.
    - 🚚 **Operations & Logistics:** Transit lead times, cancellation rates, and delivery delay correlation.
    - 🔍 **Business Investigation:** Deep-dive anomaly analysis and evidence-based recommendations.
    - 🤖 **AI Analyst:** Chat with your data using the multi-tool AI Agent (Ollama + PostgreSQL).
    """
)

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.success("✅ **Database Engine:** Connected (PostgreSQL)")
with col2:
    st.success("✅ **Analytical Marts:** Built (Facts & Dims)")
with col3:
    st.info("🔄 **AI Agent Tools:** Ready for Orchestration")

