"""Shared page chrome and chart helpers (validated categorical palette, fixed order)."""
from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

# Validated reference categorical palette (dataviz skill), always assigned in this order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PRIMARY = PALETTE[0]
SEQUENTIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]


_CSS = """
<style>
/* page canvas */
.stApp {background: radial-gradient(1200px 380px at 15% -80px, #dbe9ff 0%, rgba(219,233,255,0) 70%),
                    radial-gradient(900px 320px at 95% -60px, #d9f6ea 0%, rgba(217,246,234,0) 70%), #f6f8fc;}
.block-container {padding-top: 2.2rem;}
/* gradient page titles */
h1 {font-weight: 800 !important; letter-spacing: -.02em;
    background: linear-gradient(90deg, #1e3a8a 0%, #2a78d6 45%, #1baf7a 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent !important;}
h2, h3 {color: #1e3a8a !important; font-weight: 700 !important;}
/* sidebar */
[data-testid="stSidebar"] {background: linear-gradient(180deg, #0f1f4b 0%, #16377a 55%, #0e5d58 100%);}
[data-testid="stSidebar"] * {color: #e9effd !important;}
[data-testid="stSidebarNavLink"] {border-radius: 10px; margin: 1px 0;}
[data-testid="stSidebarNavLink"]:hover {background: rgba(255,255,255,.10) !important;}
[data-testid="stSidebarNavLink"][aria-current="page"] {background: linear-gradient(90deg, rgba(42,120,214,.55), rgba(27,175,122,.35)) !important;}
[data-testid="stSidebar"] code {background: rgba(255,255,255,.16) !important; color: #ffffff !important;}
[data-testid="stSidebar"] button {background: rgba(255,255,255,.12) !important; border: 1px solid rgba(255,255,255,.35) !important;}
/* KPI cards: colour stripe cycles blue / orange / aqua / amber */
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e2e8f3; border-left: 6px solid var(--kpi, #2a78d6);
    border-radius: 14px; padding: 14px 16px; box-shadow: 0 6px 18px rgba(30,58,138,.07);}
[data-testid="stColumn"]:nth-child(4n+1) [data-testid="stMetric"] {--kpi: #2a78d6;}
[data-testid="stColumn"]:nth-child(4n+2) [data-testid="stMetric"] {--kpi: #eb6834;}
[data-testid="stColumn"]:nth-child(4n+3) [data-testid="stMetric"] {--kpi: #1baf7a;}
[data-testid="stColumn"]:nth-child(4n+4) [data-testid="stMetric"] {--kpi: #eda100;}
[data-testid="stMetricLabel"] p {font-weight: 600; color: #475569 !important; text-transform: uppercase;
    font-size: .74rem !important; letter-spacing: .05em;}
[data-testid="stMetricValue"] {font-size: 1.75rem; font-weight: 800; color: #0f172a;}
/* white cards for bordered containers (charts, module tiles) */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {background: #ffffff;
    border-radius: 16px !important; border-color: #e2e8f3 !important; box-shadow: 0 6px 18px rgba(30,58,138,.06);}
/* tabs */
.stTabs [data-baseweb="tab"] {font-weight: 600;}
.stTabs [aria-selected="true"] {color: #2a78d6 !important;}
/* hero banner (Home) */
.hero {border-radius: 22px; padding: 34px 38px; color: #fff; margin: 4px 0 18px;
    background: linear-gradient(120deg, #0f1f4b 0%, #1d4fb3 45%, #1baf7a 100%);
    box-shadow: 0 14px 34px rgba(15,31,75,.25); position: relative; overflow: hidden;}
.hero:after {content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px;
    border-radius: 50%; background: rgba(255,255,255,.08);}
.hero .badge {display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3);
    padding: 4px 12px; border-radius: 999px; font-size: .8rem; letter-spacing: .04em;}
.hero .headline {font-size: 2.1rem; font-weight: 800; line-height: 1.15; margin: 14px 0 8px;}
.hero .sub {font-size: 1.02rem; opacity: .92; max-width: 760px;}
.hero .chips {margin-top: 20px; display: flex; flex-wrap: wrap; gap: 10px;}
.hero .chip {background: rgba(255,255,255,.95); color: #0f1f4b; border-radius: 12px; padding: 8px 14px;
    font-weight: 700; font-size: .95rem;}
.hero .chip span {display: block; font-size: .68rem; font-weight: 600; color: #64748b; text-transform: uppercase;
    letter-spacing: .05em;}
.tile-title {font-weight: 700; font-size: 1.02rem; color: #0f172a; margin-top: 4px;}
.tile-icon {width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; color: #fff;}
.tile-desc {color: #64748b; font-size: .86rem; min-height: 2.6em;}
/* ---- motion & interaction ---- */
@keyframes heroShift {0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;}}
@keyframes fadeUp {from {opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: none;}}
.hero {background-size: 220% 220% !important; animation: heroShift 16s ease infinite;}
[data-testid="stMainBlockContainer"] {animation: fadeUp .45s ease-out;}
[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;}
[data-testid="stMetric"]:hover {transform: translateY(-3px); box-shadow: 0 14px 28px rgba(30,58,138,.15);}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]):hover {
    box-shadow: 0 14px 30px rgba(30,58,138,.12); border-color: #b9cdf0 !important;}
[data-testid="stMain"] .stButton button, [data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(90deg, #2a78d6, #1baf7a); color: #fff !important; border: 0; border-radius: 10px;
    font-weight: 600; box-shadow: 0 6px 14px rgba(42,120,214,.25); transition: filter .15s ease, transform .15s ease;}
[data-testid="stMain"] .stButton button:hover, [data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover {
    filter: brightness(1.08); transform: translateY(-1px);}
[data-testid="stPageLink"] a {border-radius: 10px; background: #eef4fd; font-weight: 600;}
[data-testid="stPageLink"] a:hover {background: #dce9fb;}
.subtitle {display: inline-block; background: #ffffff; border: 1px solid #dbe5f4; color: #334155; border-radius: 999px;
    padding: 5px 14px; font-size: .88rem; margin: -6px 0 12px; box-shadow: 0 2px 8px rgba(30,58,138,.05);}
.subtitle b {color: #1d4fb3;}
[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(30,58,138,.06);}
@media (prefers-reduced-motion: reduce) {.hero, [data-testid="stMainBlockContainer"] {animation: none;}
    [data-testid="stMetric"]:hover {transform: none;}}
</style>
"""


def page(title: str, caption: str = "") -> None:
    """Common page header + sidebar. Stops the page with one clear message if Snowflake is unreachable."""
    from utils.db import connection_ok  # local import avoids a circular import

    st.set_page_config(page_title=f"BMTC | {title}", page_icon=":material/directions_bus:", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(title)
    if caption:
        st.markdown(f'<div class="subtitle"><b>&#9679;</b>&nbsp; {html.escape(caption)}</div>', unsafe_allow_html=True)
    with st.sidebar:
        st.caption("BMTC Data Warehouse · Snowflake BMTC_DW")
        st.caption("Academic capstone project")
        if st.button("Refresh data", help="Clear cached query results and reload from Snowflake"):
            st.cache_data.clear()
            st.rerun()
    ok, info = connection_ok()
    if not ok:
        st.error("Cannot reach Snowflake, so live data cannot be shown.", icon=":material/cloud_off:")
        st.caption(f"Details: {info}")
        from utils.snowflake_connection import config_sources
        st.caption(f"Settings found: {config_sources()}")
        st.markdown("Check the Snowflake settings in `.env` (or the deployment secrets) and that warehouse "
                    "`BMTC_WH` and database `BMTC_DW` exist, then press **Refresh data**.")
        st.stop()


def money(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "-"
    if abs(v) >= 1e7:
        return f"Rs {v / 1e7:.2f} Cr"
    if abs(v) >= 1e5:
        return f"Rs {v / 1e5:.2f} L"
    return f"Rs {v:,.0f}"


def num(v) -> str:
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return "-"


def show_table(df: pd.DataFrame, empty: str = "No rows match the current filters.", height: int | None = None) -> None:
    if df is None or df.empty:
        st.info(empty)
    else:
        kw = {"height": height} if height else {}
        st.dataframe(df, width="stretch", hide_index=True, **kw)


def _style(fig, height: int = 360, legend: bool = True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), bargap=0.25,
                      legend_title_text="", showlegend=legend, hovermode="closest")
    fig.update_xaxes(showgrid=False)
    # readable axis titles: DEPOT_NAME -> Depot Name; category axes of horizontal bars need no title
    for ax in list(fig.select_xaxes()) + list(fig.select_yaxes()):
        t = ax.title.text
        if t:
            ax.title.text = "" if (ax.type == "category" or t.endswith(("_NAME", "_CODE", "_NO"))) else                 t.replace("_", " ").title().replace("Km", "km").replace("Pct", "%")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


def chart(df: pd.DataFrame, kind: str, x: str, y: str, title: str, color: str | None = None,
          height: int = 360, horizontal: bool = False, **kw) -> None:
    """Render a Plotly chart, or an info box if there is no data."""
    if df is None or df.empty or x not in df or y not in df:
        st.info(f"{title}: no data for the current selection.")
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
        fig = px.pie(df, names=x, values=y, hole=0.55, title=title, color_discrete_sequence=PALETTE, **kw)
    elif kind == "scatter":
        fig = px.scatter(df, x=x, y=y, **common, **kw)
        fig.update_traces(marker_size=9, marker_line_width=1)
    elif kind == "box":
        fig = px.box(df, x=x, y=y, **common, **kw)
    else:
        raise ValueError(kind)
    _style(fig, height, legend=bool(color) or kind == "pie")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      title_font=dict(size=16, color="#1e3a8a"))
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch")
