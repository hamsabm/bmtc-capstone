"""Shared page chrome, enterprise design system, and chart helpers for BMTC Analytics."""
from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

# Enterprise BMTC Palette (validated reference categorical palette)
PALETTE = ["#2563eb", "#ea580c", "#059669", "#d97706", "#db2777", "#16a34a", "#7c3aed", "#dc2626"]
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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

.stApp {
    background: radial-gradient(1200px 420px at 15% -60px, #e2edff 0%, rgba(226,237,255,0) 70%),
                radial-gradient(900px 380px at 95% -40px, #e0f8ee 0%, rgba(224,248,238,0) 70%),
                #f8fafc !important;
    color: #0f172a;
}

.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1400px;
}

/* -------------------------------- Page Headings & Subtitles -------------------------------- */
h1 {
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    font-size: 2.15rem !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0d9488 100%);
    -webkit-background-clip: text !important;
    background-clip: text !important;
    color: transparent !important;
    margin-bottom: 0.25rem !important;
}

h2 {
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 1.45rem !important;
    letter-spacing: -0.02em;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
}

h3 {
    color: #1e293b !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
    letter-spacing: -0.01em;
}

.subtitle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    color: #475569;
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 0.85rem;
    font-weight: 500;
    margin: -4px 0 16px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
.subtitle b {
    color: #2563eb;
    font-size: 0.95rem;
}

/* -------------------------------- Sidebar Enterprise Redesign -------------------------------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090d16 0%, #0f172a 45%, #131d36 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}

[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}

[data-testid="stSidebarHeader"] {
    padding-bottom: 0.5rem;
}

[data-testid="stSidebarNavLink"] {
    border-radius: 10px;
    margin: 2px 0;
    padding: 6px 12px;
    transition: all 0.18s ease;
}

[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    transform: translateX(2px);
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: linear-gradient(90deg, rgba(37,99,235,0.45) 0%, rgba(13,148,136,0.3) 100%) !important;
    border-left: 3px solid #38bdf8 !important;
    font-weight: 700 !important;
}

[data-testid="stSidebar"] code {
    background: rgba(255,255,255,0.12) !important;
    color: #ffffff !important;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Sidebar button styling */
[data-testid="stSidebar"] button {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    color: #f8fafc !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.15s ease !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255, 255, 255, 0.15) !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
    transform: translateY(-1px);
}

/* -------------------------------- Enterprise KPI Cards -------------------------------- */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-left: 5px solid var(--kpi, #2563eb) !important;
    border-radius: 14px !important;
    padding: 16px 18px !important;
    box-shadow: 0 4px 14px rgba(15,23,42,0.04) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
}

[data-testid="stColumn"]:nth-child(4n+1) [data-testid="stMetric"] {--kpi: #2563eb;}
[data-testid="stColumn"]:nth-child(4n+2) [data-testid="stMetric"] {--kpi: #ea580c;}
[data-testid="stColumn"]:nth-child(4n+3) [data-testid="stMetric"] {--kpi: #059669;}
[data-testid="stColumn"]:nth-child(4n+4) [data-testid="stMetric"] {--kpi: #d97706;}

[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(15,23,42,0.08) !important;
}

[data-testid="stMetricLabel"] p {
    font-weight: 700 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 4px !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    letter-spacing: -0.02em !important;
}

/* -------------------------------- Card Containers & Panels -------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff !important;
    border-radius: 16px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 4px 16px rgba(15,23,42,0.04) !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]):hover {
    border-color: #cbd5e1 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.07) !important;
}

/* -------------------------------- Tabs -------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 2px;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 8px 18px !important;
    border-radius: 8px 8px 0 0 !important;
    color: #64748b !important;
    border: none !important;
    background: transparent !important;
}

.stTabs [aria-selected="true"] {
    color: #1e40af !important;
    font-weight: 700 !important;
    border-bottom: 3px solid #2563eb !important;
}

/* -------------------------------- Form Controls & Buttons -------------------------------- */
[data-testid="stMain"] .stButton button,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #0d9488 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 0.5rem 1.25rem !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.25) !important;
    transition: all 0.18s ease !important;
}

[data-testid="stMain"] .stButton button:hover,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover {
    filter: brightness(1.08);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(37,99,235,0.35) !important;
}

/* Page links */
[data-testid="stPageLink"] a {
    border-radius: 10px !important;
    background: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    font-weight: 600 !important;
    color: #1e293b !important;
    transition: all 0.15s ease !important;
}
[data-testid="stPageLink"] a:hover {
    background: #e2e8f0 !important;
    border-color: #cbd5e1 !important;
    transform: translateY(-1px);
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    overflow: hidden !important;
    box-shadow: 0 2px 10px rgba(15,23,42,0.03) !important;
}

/* -------------------------------- Home Hero Banner -------------------------------- */
.hero {
    border-radius: 20px;
    padding: 36px 42px;
    color: #ffffff;
    margin: 4px 0 22px;
    background: linear-gradient(135deg, #090d16 0%, #0f1f4b 35%, #1e40af 70%, #0d9488 100%);
    box-shadow: 0 16px 38px rgba(15,23,42,0.22);
    position: relative;
    overflow: hidden;
    background-size: 200% 200% !important;
    animation: heroGradientShift 18s ease infinite;
}

.hero:before {
    content: "";
    position: absolute;
    right: -40px;
    top: -40px;
    width: 280px;
    height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0) 70%);
}

.hero .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.25);
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.hero .headline {
    font-size: 2.35rem;
    font-weight: 800;
    line-height: 1.18;
    margin: 14px 0 10px;
    letter-spacing: -0.025em;
}

.hero .sub {
    font-size: 1.05rem;
    opacity: 0.92;
    max-width: 820px;
    line-height: 1.5;
}

.hero .chips {
    margin-top: 22px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}

.hero .chip {
    background: rgba(255, 255, 255, 0.95);
    color: #0f172a;
    border-radius: 12px;
    padding: 8px 16px;
    font-weight: 800;
    font-size: 1.05rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border: 1px solid rgba(255,255,255,0.8);
}

.hero .chip span {
    display: block;
    font-size: 0.68rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 2px;
}

/* Module Tiles */
.tile-title {
    font-weight: 700;
    font-size: 1.02rem;
    color: #0f172a;
    margin-top: 6px;
}
.tile-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    color: #ffffff;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.tile-desc {
    color: #64748b;
    font-size: 0.85rem;
    min-height: 2.8em;
    margin-top: 4px;
    line-height: 1.4;
}

/* Keyframes */
@keyframes heroGradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes pageFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

[data-testid="stMainBlockContainer"] {
    animation: pageFadeIn 0.35s ease-out;
}

@media (prefers-reduced-motion: reduce) {
    .hero, [data-testid="stMainBlockContainer"] { animation: none !important; }
}
</style>
"""


def page(title: str, caption: str = "") -> None:
    """Common page header + enterprise sidebar with user profile and health check."""
    from utils.db import connection_ok

    st.set_page_config(page_title=f"BMTC | {title}", page_icon=":material/directions_bus:", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(title)
    if caption:
        st.markdown(f'<div class="subtitle"><b>&#9679;</b>&nbsp; {html.escape(caption)}</div>', unsafe_allow_html=True)

    with st.sidebar:
        # BMTC Enterprise Branding Header
        st.markdown("""
        <div style="padding: 6px 4px 14px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: linear-gradient(135deg, #2563eb, #059669); width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; box-shadow: 0 4px 12px rgba(37,99,235,0.35);">
              🚌
            </div>
            <div>
              <div style="font-weight: 800; font-size: 1.05rem; letter-spacing: -0.02em; color: #ffffff;">BMTC ANALYTICS</div>
              <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 600; letter-spacing: 0.04em;">ENTERPRISE DATA PLATFORM</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        from utils.auth import render_sidebar_user_profile
        render_sidebar_user_profile()

        st.caption("Snowflake DW · BMTC_DW (XSMALL)")
        if st.button("🔄 Refresh Data Cache", help="Invalidate cached query results and reload fresh data from Snowflake", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    ok, info = connection_ok()
    if not ok:
        st.error("Cannot reach Snowflake warehouse, live operational data cannot be retrieved.", icon=":material/cloud_off:")
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


def _style(fig, height: int = 360, legend: bool = True):
    """Apply unified enterprise Plotly theme with dark slate labels and subtle grids."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=44, b=10),
        bargap=0.28,
        legend_title_text="",
        showlegend=legend,
        hovermode="closest",
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#334155"),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#475569"))
    for ax in list(fig.select_xaxes()) + list(fig.select_yaxes()):
        t = ax.title.text
        if t:
            ax.title.text = "" if (ax.type == "category" or t.endswith(("_NAME", "_CODE", "_NO"))) else \
                t.replace("_", " ").title().replace("Km", "km").replace("Pct", "%")
            ax.title.font = dict(size=12, color="#475569")
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.16)", zeroline=False, tickfont=dict(color="#475569"))
    return fig


def chart(df: pd.DataFrame, kind: str, x: str, y: str, title: str, color: str | None = None,
          height: int = 360, horizontal: bool = False, **kw) -> None:
    """Render a Plotly chart inside a styled card container, or an info banner if empty."""
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
        fig.update_traces(line_width=2.5)
        fig.update_layout(hovermode="x unified")
    elif kind == "area":
        fig = px.area(df, x=x, y=y, **common, **kw)
    elif kind == "pie":
        fig = px.pie(df, names=x, values=y, hole=0.55, title=title, color_discrete_sequence=PALETTE, **kw)
    elif kind == "scatter":
        fig = px.scatter(df, x=x, y=y, **common, **kw)
        fig.update_traces(marker_size=9, marker_line_width=1)
    elif kind == "box":
        fig = px.box(df, x=x, y=y, **common, **kw)
    else:
        raise ValueError(kind)
    _style(fig, height, legend=bool(color) or kind == "pie")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=15, color="#0f172a", family="Plus Jakarta Sans, sans-serif"),
    )
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch")
