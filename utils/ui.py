"""Shared page chrome, enterprise design system, and chart helpers for BMTC Analytics."""
from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

# Enterprise BMTC Palette (restrained, corporate transportation analytics)
PALETTE = ["#1e3a8a", "#0284c7", "#059669", "#d97706", "#7c3aed", "#475569", "#dc2626", "#0891b2"]
PRIMARY = PALETTE[0]
SECONDARY = "#059669"
NEUTRAL_DARK = "#0f172a"
NEUTRAL_MUTED = "#64748b"
BG_LIGHT = "#f8fafc"
CARD_BG = "#ffffff"
BORDER_COLOR = "#e2e8f0"

_CSS = """
<style>
/* -------------------------------- Base Canvas & Typography -------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

.stApp {
    background-color: #f8fafc !important;
    color: #0f172a;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1380px;
}

/* -------------------------------- Restrained Typography -------------------------------- */
h1 {
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    font-size: 1.6rem !important;
    color: #0f172a !important;
    margin-bottom: 0.2rem !important;
}

h2 {
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 1.25rem !important;
    letter-spacing: -0.015em !important;
    margin-top: 1.25rem !important;
    margin-bottom: 0.4rem !important;
}

h3 {
    color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    letter-spacing: -0.01em !important;
    margin-top: 0.85rem !important;
    margin-bottom: 0.35rem !important;
}

.subtitle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    color: #475569;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.82rem;
    font-weight: 500;
    margin: 0 0 16px 0;
}

/* -------------------------------- Enterprise Sidebar -------------------------------- */
[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid #1e293b !important;
}

[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}

[data-testid="stSidebarHeader"] {
    padding-bottom: 0.25rem;
}

[data-testid="stSidebarNavLink"] {
    border-radius: 6px;
    margin: 1px 0;
    padding: 6px 10px;
    transition: background-color 0.15s ease;
}

[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255, 255, 255, 0.06) !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: #1e293b !important;
    border-left: 3px solid #38bdf8 !important;
    font-weight: 600 !important;
}

[data-testid="stSidebar"] code {
    background: rgba(255,255,255,0.1) !important;
    color: #ffffff !important;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
}

[data-testid="stSidebar"] button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: background-color 0.15s ease !important;
}
[data-testid="stSidebar"] button:hover {
    background: #334155 !important;
    border-color: #475569 !important;
}

/* -------------------------------- Compact Professional KPI Cards -------------------------------- */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 12px 14px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03) !important;
}

[data-testid="stMetricLabel"] p {
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 2px !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    letter-spacing: -0.02em !important;
    line-height: 1.2 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
}

/* -------------------------------- Card Containers & Panels -------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff !important;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(15,23,42,0.02) !important;
}

/* -------------------------------- Tabs -------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0px;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 8px 14px !important;
    border-radius: 6px 6px 0 0 !important;
    color: #64748b !important;
    border: none !important;
    background: transparent !important;
}

.stTabs [aria-selected="true"] {
    color: #1e3a8a !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #1e3a8a !important;
}

/* -------------------------------- Form Controls & Buttons -------------------------------- */
[data-testid="stMain"] .stButton button,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
    background: #1e3a8a !important;
    color: #ffffff !important;
    border: 1px solid #1e3a8a !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.45rem 1rem !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.05) !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}

[data-testid="stMain"] .stButton button:hover,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
}

/* Page links */
[data-testid="stPageLink"] a {
    border-radius: 6px !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #1e293b !important;
    transition: background-color 0.15s ease !important;
}
[data-testid="stPageLink"] a:hover {
    background: #f1f5f9 !important;
    border-color: #cbd5e1 !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    overflow: hidden !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.02) !important;
}

/* Inputs & Selectboxes */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    border-radius: 6px !important;
    font-size: 0.88rem !important;
}
</style>
"""


def page(title: str, caption: str = "") -> None:
    """Common enterprise page header with sidebar branding, health check and identity."""
    from utils.db import connection_ok

    st.set_page_config(page_title=f"BMTC | {title}", page_icon=":material/directions_bus:", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(title)
    if caption:
        st.markdown(f'<div class="subtitle">{html.escape(caption)}</div>', unsafe_allow_html=True)

    with st.sidebar:
        # BMTC Enterprise Branding
        st.markdown("""
        <div style="padding: 10px 4px 14px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;">
          <div style="font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: #94a3b8; font-weight: 700;">BANGALORE METROPOLITAN</div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; margin-top: 2px;">BMTC INTELLIGENCE</div>
          <div style="display: flex; align-items: center; gap: 6px; margin-top: 6px;">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
            <span style="font-size: 0.72rem; color: #cbd5e1; font-weight: 500;">Snowflake DW &bull; Online</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        from utils.auth import render_sidebar_user_profile
        render_sidebar_user_profile()

        st.caption("Snowflake DW &bull; BMTC_DW (X-Small)")
        if st.button("Refresh Data Cache", help="Invalidate cached query results and reload fresh data from Snowflake", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    ok, info = connection_ok()
    if not ok:
        st.error("Cannot reach Snowflake warehouse. Live operational data cannot be retrieved.", icon=":material/cloud_off:")
        st.caption(f"Details: {info}")
        from utils.snowflake_connection import config_sources
        st.caption(f"Settings found: {config_sources()}")
        st.markdown("Verify the Snowflake credentials in `.env` (or Streamlit deployment secrets) and that warehouse `BMTC_WH` is running, then press **Refresh Data Cache**.")
        st.stop()


def money(v) -> str:
    """Format currency values cleanly into Crores, Lakhs or Thousands."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "-"
    if abs(v) >= 1e7:
        return f"₹{v / 1e7:.2f} Cr"
    if abs(v) >= 1e5:
        return f"₹{v / 1e5:.2f} L"
    return f"₹{v:,.0f}"


def num(v) -> str:
    """Format numeric values with comma separators."""
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return "-"


def show_table(df: pd.DataFrame, empty: str = "No records match the active filters.", height: int | None = None) -> None:
    """Render an enterprise styled table or informative message if empty."""
    if df is None or df.empty:
        st.info(empty, icon=":material/info:")
    else:
        kw = {"height": height} if height else {}
        st.dataframe(df, width="stretch", hide_index=True, **kw)


def _style(fig, height: int = 340, legend: bool = True):
    """Apply unified enterprise Plotly theme with dark slate labels and subtle grids."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=36, b=10),
        bargap=0.25,
        legend_title_text="",
        showlegend=legend,
        hovermode="closest",
        font=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#475569"),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#475569", size=11))
    for ax in list(fig.select_xaxes()) + list(fig.select_yaxes()):
        t = ax.title.text
        if t:
            ax.title.text = "" if (ax.type == "category" or t.endswith(("_NAME", "_CODE", "_NO"))) else \
                t.replace("_", " ").title().replace("Km", "km").replace("Pct", "%")
            ax.title.font = dict(size=11, color="#475569")
    fig.update_yaxes(gridcolor="rgba(226, 232, 240, 0.8)", zeroline=False, tickfont=dict(color="#475569", size=11))
    return fig


def chart(df: pd.DataFrame, kind: str, x: str, y: str, title: str, color: str | None = None,
          height: int = 340, horizontal: bool = False, **kw) -> None:
    """Render a Plotly chart inside a clean card container, or an info banner if empty."""
    if df is None or df.empty or x not in df or y not in df:
        st.info(f"{title}: No records available for the active selection.", icon=":material/info:")
        return
    common = dict(title=title, color_discrete_sequence=PALETTE)
    if color:
        common["color"] = color
    if kind == "bar":
        fig = px.bar(df, x=y if horizontal else x, y=x if horizontal else y,
                     orientation="h" if horizontal else "v", **common, **kw)
        fig.update_traces(marker_line_width=0)
        if horizontal:
            fig.update_yaxes(categoryorder="total ascending")
    elif kind == "line":
        fig = px.line(df, x=x, y=y, **common, **kw)
        fig.update_traces(line_width=2)
        fig.update_layout(hovermode="x unified")
    elif kind == "area":
        fig = px.area(df, x=x, y=y, **common, **kw)
    elif kind == "pie":
        fig = px.pie(df, names=x, values=y, hole=0.58, title=title, color_discrete_sequence=PALETTE, **kw)
    elif kind == "scatter":
        fig = px.scatter(df, x=x, y=y, **common, **kw)
        fig.update_traces(marker_size=8, marker_line_width=1)
    elif kind == "box":
        fig = px.box(df, x=x, y=y, **common, **kw)
    else:
        raise ValueError(kind)
    _style(fig, height, legend=bool(color) or kind == "pie")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=14, color="#0f172a", family="Plus Jakarta Sans, sans-serif"),
    )
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch")
