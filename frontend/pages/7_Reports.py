"""
InsightIQ: Executive Business Reports & Export Studio.
Fulfills Section 8.F of Master Prompt:
- Weekly / Executive Business Summaries
- Key Metrics & KPIs
- Analytical Findings & Strategic Recommendations
- Downloadable Markdown & JSON reports
"""

import sys
import json
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.reporting.report_generator import ReportGeneratorService
from frontend.components.styles import apply_theme

st.set_page_config(page_title="Executive Reports | InsightIQ", page_icon="📑", layout="wide")
apply_theme()

st.title("📑 Executive Reports & Intelligence Briefings")
st.markdown("Generate, inspect, and export formal executive summaries, performance audits, and strategic recommendations.")

col_type, col_action = st.columns([3, 1])
with col_type:
    report_type = st.selectbox("Select Report Template:", [
        "Executive Business Performance Report (Comprehensive)",
        "Operational Health & Satisfaction Briefing",
        "Quarterly Logistics & Seller Audit",
    ])

with col_action:
    generate_btn = st.button("📄 Generate Report", type="primary")

# Load and compile report
with st.spinner("Compiling live metrics, analytical correlations, and executive synthesis..."):
    report_data = ReportGeneratorService.generate_executive_business_report()

st.success(f"Report compiled successfully at **{report_data['timestamp']}**")

# Export Buttons
col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 3])
with col_dl1:
    st.download_button(
        label="📥 Download Markdown",
        data=report_data["markdown"],
        file_name=f"insightiq_executive_report_{report_data['timestamp'].replace(':', '-').replace(' ', '_')}.md",
        mime="text/markdown",
    )

with col_dl2:
    st.download_button(
        label="📥 Export JSON Metrics",
        data=json.dumps(report_data["metrics"], indent=2, default=str),
        file_name=f"insightiq_metrics_{report_data['timestamp'].replace(':', '-').replace(' ', '_')}.json",
        mime="application/json",
    )

st.markdown("---")

# Render Report Markdown
st.markdown(report_data["markdown"])
