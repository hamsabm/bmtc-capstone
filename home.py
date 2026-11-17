"""Home page: hero banner with live KPIs, role switcher, module tiles, architecture, table inventory."""
import html

import streamlit as st

from utils import queries as Q
from utils.auth import render_role_switcher_banner
from utils.db import connection_ok, query
from utils.ui import money, num, page, show_table

page("BMTC Data Warehouse & Analytics System",
     "Operations, fleet, revenue and passenger analytics on Snowflake")

render_role_switcher_banner()

ok, info = connection_ok()   # page() already stopped the script if the connection failed

# ---------------------------------------------------------------- hero (all numbers are live from Snowflake)
kpi = query(Q.KPIS)
chips = ""
if not kpi.empty:
    k = kpi.iloc[0]
    chips = "".join(
        f'<div class="chip"><span>{html.escape(lbl)}</span>{html.escape(val)}</div>'
        for lbl, val in [("Buses", num(k.TOTAL_BUSES)), ("Routes", num(k.TOTAL_ROUTES)),
                         ("Trips", num(k.TOTAL_TRIPS)), ("Tickets", num(k.TOTAL_TICKETS)),
                         ("Ticket revenue", money(k.TICKET_REVENUE)), ("On-time trips", f"{k.ON_TIME_PCT}%")])
st.markdown(f"""
<div class="hero">
  <div class="badge">SNOWFLAKE · PYTHON · STREAMLIT · POWER BI · RBAC</div>
  <div class="headline">Bengaluru bus operations,<br/>one live data platform.</div>
  <div class="sub">Fleet, routes, ticketing, fuel, maintenance, passes, passenger complaints, and dedicated roles for Driver, Conductor, Mechanic, Depot Manager & Admin -
  loaded, governed and analysed in Snowflake, explored here in real time.</div>
  <div class="chips">{chips}</div>
</div>
""", unsafe_allow_html=True)

st.success(f"Connected to Snowflake - {info}", icon=":material/check_circle:")

# ---------------------------------------------------------------- role portals & module tiles
st.subheader("Role-Based Portals & System Modules")
TILES = [
    ("app_pages/9_Driver_Portal.py", "Driver Portal", "🚌", "Duty log, safety checklist, trip status", ":material/badge:", "#1baf7a"),
    ("app_pages/10_Conductor_ETM.py", "Conductor ETM", "🎟️", "Issue tickets, Shakti scheme, pass scanner", ":material/confirmation_number:", "#eda100"),
    ("app_pages/11_Depot_Operations.py", "Depot Command", "🏢", "Morning turnout, crew & bus dispatch", ":material/domain:", "#eb6834"),
    ("app_pages/12_Staff_Directory.py", "Staff Directory", "🧑‍💼", "Workforce directory & masked payroll", ":material/badge:", "#6250d6"),
    ("app_pages/1_Dashboard.py", "Dashboard", "📊", "Live KPIs and headline charts", ":material/dashboard:", "#2a78d6"),
    ("app_pages/2_Bus_Management.py", "Bus Management", "🚍", "Fleet search, depots, change bus status", ":material/directions_bus:", "#eb6834"),
    ("app_pages/3_Routes_Trips.py", "Routes & Trips", "🗺️", "Route detail, top/bottom routes, trip log", ":material/route:", "#1baf7a"),
    ("app_pages/4_Ticket_Analytics.py", "Ticket Analytics", "📈", "Revenue, payment mix, hourly trends", ":material/analytics:", "#eda100"),
    ("app_pages/5_Fuel_Maintenance.py", "Fuel & Maintenance", "⛽", "Efficiency (Python UDF), workshop jobs", ":material/build:", "#e87ba4"),
    ("app_pages/6_Passenger_Complaints.py", "Passengers & Complaints", "👥", "Passes, JSON complaints, triage", ":material/groups:", "#008300"),
    ("app_pages/7_Advanced_Analytics.py", "Advanced Analytics", "📉", "CTEs, window functions, subqueries", ":material/query_stats:", "#6250d6"),
    ("app_pages/8_Data_Management.py", "Data Management", "🗄️", "Time Travel, clone, stream & task", ":material/database:", "#e34948"),
]
for row in range(0, len(TILES), 4):
    cols = st.columns(4)
    for col, (path, title, emoji, desc, icon, colour) in zip(cols, TILES[row:row + 4]):
        with col, st.container(border=True):
            st.markdown(f'<div class="tile-icon" style="background:{colour}">{emoji}</div>'
                        f'<div class="tile-title">{title}</div><div class="tile-desc">{desc}</div>',
                        unsafe_allow_html=True)
            st.page_link(path, label=f"Open {title}", icon=icon)

# ---------------------------------------------------------------- architecture + inventory
left, right = st.columns([1, 1])
with left:
    st.subheader("How it works")
    st.markdown("""
1. **Role-Based Access Control (RBAC)** - Tailored portals for **Driver**, **Conductor**, **Mechanic**, **Depot Manager**, **Supervisor**, and **Admin**.
2. **Data sources** - CSV and JSON files (fleet, trips, tickets, fuel, complaints)
3. **Snowflake loading** - file formats → internal stage → `COPY INTO` / Snowpipe → validated tables
4. **Warehouse** - `BMTC_DW` with `BUS`, `TRIP`, `PASSENGER` schemas, views and JSON (VARIANT)
5. **Automation & governance** - streams, tasks, Time Travel, clones, roles, masking
6. **Python** - connector, Python UDFs and a Snowpark procedure
7. **This app & Power BI** - live analytics and operational data entry
""")
with right:
    st.subheader("Tables in BMTC_DW")
    tables = query("""
    SELECT TABLE_SCHEMA AS SCHEMA_NAME, TABLE_NAME, ROW_COUNT,
           IFF(IS_TRANSIENT = 'YES', 'TRANSIENT', 'PERMANENT') AS TABLE_KIND
    FROM BMTC_DW.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA IN ('BUS', 'TRIP', 'PASSENGER') AND TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME""")
    if not tables.empty:
        st.metric("Rows across project tables", num(tables["ROW_COUNT"].sum()))
    show_table(tables, height=320)
