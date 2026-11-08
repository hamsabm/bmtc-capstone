"""Shared page chrome and chart helpers (validated categorical palette, fixed order)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

# Validated reference categorical palette (dataviz skill), always assigned in this order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PRIMARY = PALETTE[0]
SEQUENTIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]


_CSS = """
<style>
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); border-radius: 8px; padding: 10px 14px;}
[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
"""


def page(title: str, caption: str = "") -> None:
    """Common page header + sidebar. Stops the page with one clear message if Snowflake is unreachable."""
    from utils.db import connection_ok  # local import avoids a circular import

    st.set_page_config(page_title=f"BMTC | {title}", page_icon=":material/directions_bus:", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(title)
    if caption:
        st.caption(caption)
    with st.sidebar:
        st.caption("BMTC Data Warehouse · Snowflake `BMTC_DW`")
        st.caption("Synthetic academic dataset - not official BMTC operational data.")
        if st.button("Refresh data", help="Clear cached query results and reload from Snowflake"):
            st.cache_data.clear()
            st.rerun()
    ok, info = connection_ok()
    if not ok:
        st.error("Cannot reach Snowflake, so live data cannot be shown.", icon=":material/cloud_off:")
        st.caption(f"Details: {info}")
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
    st.plotly_chart(fig, width="stretch")
