"""
InsightIQ Frontend UI Theme & Shared Component Helpers.

Provides styling, responsive metric cards, chart theming, and layout utilities.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Color Palette
PRIMARY_COLOR = "#1E3A8A"     # Deep Blue
SECONDARY_COLOR = "#0D9488"   # Teal
ACCENT_COLOR = "#F59E0B"      # Amber
BACKGROUND_COLOR = "#0F172A"  # Dark Slate
CARD_BG = "#1E293B"           # Card Slate
TEXT_COLOR = "#F8FAFC"        # Off-white

CUSTOM_CSS = """
<style>
    /* Global styles */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Metric Card Styling */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        border-color: #0D9488;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .metric-sub {
        color: #38BDF8;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* Section Header */
    .section-header {
        border-bottom: 2px solid #334155;
        padding-bottom: 8px;
        margin-top: 24px;
        margin-bottom: 20px;
        color: #38BDF8;
        font-size: 1.35rem;
        font-weight: 700;
    }
</style>
"""


def apply_theme():
    """Injects custom CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def metric_card(title: str, value: str, sub: str = ""):
    """Renders a custom styled metric card."""
    sub_html = f"<div class='metric-sub'>{sub}</div>" if sub else ""
    card_html = f"""
    <div class='metric-card'>
        <div class='metric-title'>{title}</div>
        <div class='metric-value'>{value}</div>
        {sub_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def configure_plotly_theme(fig: go.Figure) -> go.Figure:
    """Applies a consistent dark theme to Plotly figures."""
    fig.update_layout(
        paper_bgcolor="#1E293B",
        plot_bgcolor="#1E293B",
        font=dict(color="#F8FAFC", family="Inter"),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    )
    return fig
