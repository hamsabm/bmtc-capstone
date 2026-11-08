import streamlit as st

from utils.db import query
from utils.queries import ADVANCED
from utils.ui import chart, page, show_table

page("Advanced Analytics",
     "Joins, subqueries, CTEs, aggregates, GROUP BY / HAVING, CASE and window functions on live data")

name = st.selectbox("Analysis", list(ADVANCED))
sql = ADVANCED[name]
with st.expander("SQL", expanded=False):
    st.code(sql.strip(), language="sql")

df = query(sql)
st.caption(f"{len(df)} rows")
show_table(df, "This analysis returned no rows.", height=420)

# A chart for analyses with an obvious visual form
if not df.empty:
    if "MONTH" in df and "REVENUE" in df:
        chart(df, "line", "MONTH", "RUNNING_REVENUE", "Running revenue", markers=True, hover_data=["REVENUE", "MOM_CHANGE_PCT"])
    elif "RANK_IN_CATEGORY" in df:
        chart(df[df["RANK_IN_CATEGORY"] <= 3], "bar", "ROUTE_CODE", "REVENUE", "Top 3 routes per category",
              color="ROUTE_CATEGORY", horizontal=True, height=420)
    elif "PCT_VS_TYPE" in df:
        chart(df, "box", "BUS_TYPE", "PCT_VS_TYPE", "Bus efficiency vs bus-type average (%)")
    elif "COST_PER_BUS" in df:
        chart(df, "bar", "DEPOT_NAME", "COST_PER_BUS", "Maintenance cost per bus (Rs)", horizontal=True)
    elif "PER_1000_PAX" in df:
        chart(df.head(15), "bar", "ROUTE_CODE", "PER_1000_PAX", "Complaints per 1,000 passengers (top 15)",
              horizontal=True, hover_data=["COMPLAINTS"])
    elif "AVG_RIDES_PER_PASS" in df:
        chart(df, "bar", "PASS_TYPE", "AVG_RIDES_PER_PASS", "Average rides per pass", horizontal=True)
    elif "ON_TIME_PCT" in df:
        chart(df, "bar", "PERIOD", "ON_TIME_PCT", "On-time trips (%)")
