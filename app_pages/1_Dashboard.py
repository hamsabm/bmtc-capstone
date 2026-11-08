import pandas as pd
import streamlit as st

from utils import queries as Q
from utils.db import query
from utils.ui import chart, money, num, page

page("Dashboard", "Live KPIs from TRIP.V_DASHBOARD_KPIS and analytical views")

kpi = query(Q.KPIS)
if kpi.empty:
    st.stop()
k = kpi.iloc[0]

# Period switch: re-filters the monthly trend data client-side, instantly
period = st.segmented_control("Trend period", ["Last 3 months", "Last 6 months", "All 12 months"],
                              default="All 12 months", key="dash_period")
n_months = {"Last 3 months": 3, "Last 6 months": 6}.get(period or "All 12 months", 12)


def last_months(df: pd.DataFrame, col: str = "MONTH") -> pd.DataFrame:
    if df.empty or col not in df:
        return df
    months = sorted(pd.to_datetime(df[col]).dt.to_period("M").unique())[-n_months:]
    return df[pd.to_datetime(df[col]).dt.to_period("M").isin(months)]


trend = last_months(query(Q.MONTHLY_TRENDS))


def spark(col: str):
    return trend[col].fillna(0).tolist() if not trend.empty and col in trend else None


r1 = st.columns(4)
r1[0].metric("Total buses", num(k.TOTAL_BUSES), f"{num(k.ACTIVE_BUSES)} active", delta_color="off", delta_arrow="off")
r1[1].metric("Total trips", num(k.TOTAL_TRIPS), f"{k.ON_TIME_PCT}% on time", delta_color="off", delta_arrow="off",
             chart_data=spark("TRIPS"), chart_type="area")
r1[2].metric("Total tickets", num(k.TOTAL_TICKETS), money(k.TICKET_REVENUE), delta_color="off", delta_arrow="off",
             chart_data=spark("TICKETS"), chart_type="area")
r1[3].metric("Total routes", num(k.TOTAL_ROUTES))
r2 = st.columns(4)
r2[0].metric("Passenger passes", num(k.TOTAL_PASSES), f"{num(k.ACTIVE_PASSES)} active", delta_color="off",
             delta_arrow="off", chart_data=spark("PASSES"), chart_type="bar")
r2[1].metric("Complaints", num(k.TOTAL_COMPLAINTS), f"{num(k.OPEN_COMPLAINTS)} open", delta_color="off",
             delta_arrow="off", chart_data=spark("COMPLAINTS"), chart_type="bar")
r2[2].metric("Fuel records", num(k.TOTAL_FUEL_RECORDS), money(k.FUEL_COST), delta_color="off", delta_arrow="off",
             chart_data=spark("FUEL_COST"), chart_type="area")
r2[3].metric("Maintenance records", num(k.TOTAL_MAINTENANCE_RECORDS), money(k.MAINTENANCE_COST), delta_color="off",
             delta_arrow="off", chart_data=spark("MAINT_COST"), chart_type="area")
st.caption(f"Mini charts show monthly trends for the selected period ({n_months} months). Headline numbers cover all data.")

st.divider()
c1, c2 = st.columns(2)
with c1:
    chart(query(Q.BUSES_BY_DEPOT), "bar", "DEPOT_NAME", "BUSES", "Buses by depot and type",
          color="BUS_TYPE", horizontal=True, height=400)
with c2:
    chart(query(Q.TOP_ROUTES_BY_TRIPS), "bar", "ROUTE_CODE", "TRIPS", "Trips by route (top 15)",
          horizontal=True, height=400, hover_data=["ROUTE_CATEGORY", "PASSENGERS", "REVENUE"])

c3, c4 = st.columns(2)
with c3:
    chart(last_months(query(Q.MONTHLY_TICKETS)), "line", "MONTH", "TICKETS", f"Ticket activity per month ({period or 'All 12 months'})",
          markers=True, hover_data=["REVENUE"])
with c4:
    chart(last_months(query(Q.MONTHLY_FUEL)), "line", "MONTH", "FUEL_COST", f"Fuel / charging cost per month, Rs ({period or 'All 12 months'})",
          color="FUEL_TYPE", markers=True)

c5, c6 = st.columns(2)
with c5:
    chart(query(Q.MAINT_BY_TYPE), "bar", "MAINTENANCE_TYPE", "JOBS", "Maintenance jobs by type",
          horizontal=True, hover_data=["COST"])
with c6:
    chart(query(Q.COMPLAINTS_BY_CATEGORY), "bar", "CATEGORY", "COMPLAINTS", "Complaints by category",
          horizontal=True, hover_data=["OPEN_COMPLAINTS"])
