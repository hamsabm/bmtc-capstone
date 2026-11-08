import streamlit as st

from utils import queries as Q
from utils.db import query
from utils.ui import chart, money, num, page

page("Dashboard", "Live KPIs from TRIP.V_DASHBOARD_KPIS and analytical views")

kpi = query(Q.KPIS)
if kpi.empty:
    st.stop()
k = kpi.iloc[0]

r1 = st.columns(4)
r1[0].metric("Total buses", num(k.TOTAL_BUSES), f"{num(k.ACTIVE_BUSES)} active", delta_color="off", delta_arrow="off")
r1[1].metric("Total routes", num(k.TOTAL_ROUTES))
r1[2].metric("Total trips", num(k.TOTAL_TRIPS), f"{k.ON_TIME_PCT}% on time", delta_color="off", delta_arrow="off")
r1[3].metric("Total tickets", num(k.TOTAL_TICKETS), money(k.TICKET_REVENUE), delta_color="off", delta_arrow="off")
r2 = st.columns(4)
r2[0].metric("Passenger passes", num(k.TOTAL_PASSES), f"{num(k.ACTIVE_PASSES)} active", delta_color="off", delta_arrow="off")
r2[1].metric("Complaints", num(k.TOTAL_COMPLAINTS), f"{num(k.OPEN_COMPLAINTS)} open", delta_color="off", delta_arrow="off")
r2[2].metric("Fuel records", num(k.TOTAL_FUEL_RECORDS), money(k.FUEL_COST), delta_color="off", delta_arrow="off")
r2[3].metric("Maintenance records", num(k.TOTAL_MAINTENANCE_RECORDS), money(k.MAINTENANCE_COST), delta_color="off", delta_arrow="off")

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
    chart(query(Q.MONTHLY_TICKETS), "line", "MONTH", "TICKETS", "Ticket activity per month",
          markers=True, hover_data=["REVENUE"])
with c4:
    chart(query(Q.MONTHLY_FUEL), "line", "MONTH", "FUEL_COST", "Fuel / charging cost per month (Rs)",
          color="FUEL_TYPE", markers=True)

c5, c6 = st.columns(2)
with c5:
    chart(query(Q.MAINT_BY_TYPE), "bar", "MAINTENANCE_TYPE", "JOBS", "Maintenance jobs by type",
          horizontal=True, hover_data=["COST"])
with c6:
    chart(query(Q.COMPLAINTS_BY_CATEGORY), "bar", "CATEGORY", "COMPLAINTS", "Complaints by category",
          horizontal=True, hover_data=["OPEN_COMPLAINTS"])
