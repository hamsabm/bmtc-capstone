"""Home page: enterprise hero banner with live KPIs, role switcher, module cards, architecture and live database inventory."""
import html

import streamlit as st

from utils import queries as Q
from utils.auth import get_current_user, render_role_switcher_banner
from utils.db import connection_ok, query
from utils.ui import money, num, page, show_table

page("BMTC Data Warehouse & Analytics System",
     "Unified operations, fleet, revenue and passenger intelligence on Snowflake")

# ------------------------------------------------ Role Switcher Bar
render_role_switcher_banner()

ok, info = connection_ok()

# ------------------------------------------------ Live Enterprise Hero Banner
kpi = query(Q.KPIS)
chips = ""
if not kpi.empty:
    k = kpi.iloc[0]
    chip_items = [
        ("🚌 Total Buses", num(k.TOTAL_BUSES), f"{num(k.ACTIVE_BUSES)} in service"),
        ("🗺️ Active Routes", num(k.TOTAL_ROUTES), "City & Airport lines"),
        ("🚦 Completed Trips", num(k.TOTAL_TRIPS), f"{k.ON_TIME_PCT}% on-time rate"),
        ("🎟️ Tickets Issued", num(k.TOTAL_TICKETS), "Passenger boardings"),
        ("💰 Fare Revenue", money(k.TICKET_REVENUE), "Direct collection"),
        ("⏱️ On-Time Rate", f"{k.ON_TIME_PCT}%", "Arrival <= 5 min"),
    ]
    chips = "".join(
        f'<div class="chip"><span>{html.escape(lbl)}</span>{html.escape(val)}'
        f'<div style="font-size: 0.65rem; color: #64748b; font-weight: 500; margin-top: 1px;">{html.escape(sub)}</div></div>'
        for lbl, val, sub in chip_items
    )

st.markdown(f"""
<div class="hero">
  <div class="badge">
    <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981; margin-right:6px;"></span>
    SNOWFLAKE DW &bull; PYTHON &bull; STREAMLIT &bull; POWER BI &bull; RBAC
  </div>
  <div class="headline">BMTC Data Warehouse & Analytics System</div>
  <div class="sub">Unified analytics for Bengaluru bus operations, fleet, revenue and passenger intelligence.
  Loaded, governed and analysed in Snowflake &mdash; explored here in real time.</div>
  <div class="chips">{chips}</div>
</div>
""", unsafe_allow_html=True)

st.success(f"Connected to Snowflake &mdash; {info}", icon=":material/verified:")

# ------------------------------------------------ Active Role Quick Action Card
curr_user = get_current_user()
curr_role = curr_user.get("role", "Admin")

if curr_role == "Driver":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(5,150,105,0.08) 0%, rgba(16,185,129,0.03) 100%); border: 1px solid #10b981; border-left: 5px solid #059669; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <div style="font-weight: 800; font-size: 1.15rem; color: #065f46;">
                🚌 Welcome back, {curr_user.get('name')} (<code>{curr_user.get('employee_code')}</code>)
              </div>
              <div style="font-size: 0.88rem; color: #047857; margin-top: 4px;">
                Base Depot: <b>{curr_user.get('depot_name')}</b> &bull; Assigned Routes: <b>146B, MF-167B, V-114A, MF-106B</b>
              </div>
            </div>
            <div style="display:flex; gap:10px;">
              <span style="background: #059669; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 700; font-size: 0.82rem;">🟢 DRIVER DUTY ACTIVE</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif curr_role == "Conductor":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(217,119,6,0.08) 0%, rgba(245,158,11,0.03) 100%); border: 1px solid #f59e0b; border-left: 5px solid #d97706; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <div style="font-weight: 800; font-size: 1.15rem; color: #78350f;">
                🎟️ Welcome back, {curr_user.get('name')} (<code>{curr_user.get('employee_code')}</code>)
              </div>
              <div style="font-size: 0.88rem; color: #92400e; margin-top: 4px;">
                Base Depot: <b>{curr_user.get('depot_name')}</b> &bull; Terminal: <b>ETM-BLR-013</b> &bull; Assigned Routes: <b>146B, MF-167B, V-114A, MF-106B</b>
              </div>
            </div>
            <div style="display:flex; gap:10px;">
              <span style="background: #d97706; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 700; font-size: 0.82rem;">🟡 ETM SESSION READY</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif curr_role == "Depot Manager":
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(234,88,12,0.08) 0%, rgba(249,115,22,0.03) 100%); border: 1px solid #fb923c; border-left: 5px solid #ea580c; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <div style="font-weight: 800; font-size: 1.15rem; color: #7c2d12;">
                🏢 Depot Command Center &bull; {curr_user.get('name')}
              </div>
              <div style="font-size: 0.88rem; color: #9a3412; margin-top: 4px;">
                Facility: <b>{curr_user.get('depot_name')}</b> &bull; Morning Turnout: <b>100% On-Schedule</b>
              </div>
            </div>
            <div style="display:flex; gap:10px;">
              <span style="background: #ea580c; color: white; padding: 5px 12px; border-radius: 8px; font-weight: 700; font-size: 0.82rem;">🟠 DEPOT 01 COMMAND</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------ Portals & Modules Section
st.subheader("System Portals & Operations Modules")
st.caption("Access role-tailored workspaces or dive into enterprise fleet and revenue intelligence.")

tab_roles, tab_ops, tab_dw = st.tabs([
    "🧑‍💼 Role-Based Portals",
    "📊 Fleet & Operations Intelligence",
    "🗄️ Platform & Data Governance",
])

with tab_roles:
    ROLE_TILES = [
        ("app_pages/9_Driver_Portal.py", "Driver Portal", "🚌", "Duty schedule, live trip logger, vehicle safety checklist (DVIR)", ":material/badge:", "#059669"),
        ("app_pages/10_Conductor_ETM.py", "Conductor ETM", "🎟️", "Electronic Ticketing Machine, Shakti scheme zero-fare, QR pass validator", ":material/confirmation_number:", "#d97706"),
        ("app_pages/11_Depot_Operations.py", "Depot Command", "🏢", "Morning turnout, fleet readiness, crew & bus dispatch roster", ":material/domain:", "#ea580c"),
        ("app_pages/12_Staff_Directory.py", "Staff Directory", "🧑‍💼", "Workforce directory by role and depot with masked payroll analytics", ":material/badge:", "#7c3aed"),
    ]
    cols = st.columns(4)
    for col, (path, title, emoji, desc, icon, colour) in zip(cols, ROLE_TILES):
        with col, st.container(border=True):
            st.markdown(f'<div class="tile-icon" style="background:{colour}">{emoji}</div>'
                        f'<div class="tile-title">{title}</div><div class="tile-desc">{desc}</div>',
                        unsafe_allow_html=True)
            st.page_link(path, label=f"Launch {title} →", icon=icon)

with tab_ops:
    OPS_TILES = [
        ("app_pages/1_Dashboard.py", "Executive Dashboard", "📊", "Live operational KPIs, monthly sparklines and multi-period trends", ":material/dashboard:", "#2563eb"),
        ("app_pages/2_Bus_Management.py", "Bus Management", "🚍", "Fleet inventory, depot allocation, status updates with transactional audit", ":material/directions_bus:", "#ea580c"),
        ("app_pages/3_Routes_Trips.py", "Routes & Trips", "🗺️", "Route performance ranking, delay patterns, and live trip execution log", ":material/route:", "#059669"),
        ("app_pages/4_Ticket_Analytics.py", "Ticket Analytics", "📈", "Revenue dynamics, payment mix (Cash/UPI/Cards), hourly peak analysis", ":material/analytics:", "#d97706"),
        ("app_pages/5_Fuel_Maintenance.py", "Fuel & Maintenance", "⛽", "Python UDF fuel efficiency, EV charging metrics, and workshop job orders", ":material/build:", "#db2777"),
        ("app_pages/6_Passenger_Complaints.py", "Passenger Grievances", "👥", "Smart pass validations, semi-structured JSON complaint triage queue", ":material/groups:", "#16a34a"),
    ]
    for row in range(0, len(OPS_TILES), 3):
        cols = st.columns(3)
        for col, (path, title, emoji, desc, icon, colour) in zip(cols, OPS_TILES[row:row + 3]):
            with col, st.container(border=True):
                st.markdown(f'<div class="tile-icon" style="background:{colour}">{emoji}</div>'
                            f'<div class="tile-title">{title}</div><div class="tile-desc">{desc}</div>',
                            unsafe_allow_html=True)
                st.page_link(path, label=f"Open {title} →", icon=icon)

with tab_dw:
    DW_TILES = [
        ("app_pages/7_Advanced_Analytics.py", "Advanced SQL Analytics", "📉", "CTEs, window functions, correlated subqueries, and running totals", ":material/query_stats:", "#7c3aed"),
        ("app_pages/8_Data_Management.py", "Data Platform Console", "🗄️", "Time Travel, zero-copy clones, streams, tasks, Snowpipe and security", ":material/database:", "#dc2626"),
    ]
    cols = st.columns(2)
    for col, (path, title, emoji, desc, icon, colour) in zip(cols, DW_TILES):
        with col, st.container(border=True):
            st.markdown(f'<div class="tile-icon" style="background:{colour}">{emoji}</div>'
                        f'<div class="tile-title">{title}</div><div class="tile-desc">{desc}</div>',
                        unsafe_allow_html=True)
            st.page_link(path, label=f"Inspect {title} →", icon=icon)

st.divider()

# ------------------------------------------------ Architecture & Live Inventory
col_arch, col_inv = st.columns([1, 1])

with col_arch:
    with st.container(border=True):
        st.subheader("Data Architecture & Pipeline")
        st.markdown("""
1. **Data Sources** &mdash; Standardized CSV and JSON feeds covering fleet, crew, trips, tickets, fuel, and passenger complaints.
2. **Snowflake Ingestion** &mdash; Internal stage &rarr; `COPY INTO` &rarr; transient staging tables &rarr; validated core data warehouse.
3. **Enterprise Warehouse** &mdash; `BMTC_DW` structured into `BUS`, `TRIP`, `PASSENGER`, `STAGING`, and `GOVERNANCE` schemas.
4. **CDC Automation & Tasks** &mdash; Snowflake Streams capture delta changes; scheduled Tasks automatically refresh summary aggregates.
5. **Security & RBAC** &mdash; Role hierarchy (`BMTC_VIEWER` &rarr; `ANALYST` &rarr; `MANAGER` &rarr; `ADMIN`), masking policies, and row access policies.
6. **Python & Snowpark** &mdash; Vectorized Python UDFs for fuel efficiency classification and complaint urgency scoring.
7. **BI & Dashboards** &mdash; Live Streamlit user interfaces and direct Power BI Desktop semantic models.
        """)

with col_inv:
    with st.container(border=True):
        st.subheader("Live Database Inventory (BMTC_DW)")
        tables = query("""
        SELECT TABLE_SCHEMA AS SCHEMA_NAME, TABLE_NAME, ROW_COUNT,
               IFF(IS_TRANSIENT = 'YES', 'TRANSIENT', 'PERMANENT') AS TABLE_KIND
        FROM BMTC_DW.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('BUS', 'TRIP', 'PASSENGER') AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME""")
        if not tables.empty:
            st.metric("Total records across permanent tables", num(tables["ROW_COUNT"].sum()), "100% synchronized with Snowflake")
        show_table(tables, height=280)
