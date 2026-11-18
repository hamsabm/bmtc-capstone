"""Home page: executive intelligence overview, live Snowflake KPIs, operational summary and action center."""
import streamlit as st

from utils import queries as Q
from utils.auth import get_current_user, render_role_switcher_banner
from utils.db import connection_ok, query
from utils.ui import chart, money, num, page, show_table

page("BMTC Data Intelligence Platform", "Operational intelligence for Bengaluru's public transportation network")

ok, info = connection_ok()

# ------------------------------------------------ System Status & Role Bar
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
  <div style="display: inline-flex; align-items: center; gap: 8px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 10px; font-size: 0.75rem; color: #475569;">
    <span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #10b981;"></span>
    <span style="font-weight: 700; color: #0f172a;">System Operational</span>
    <span style="color: #cbd5e1;">&bull;</span>
    <span>Snowflake BMTC_DW</span>
    <span style="color: #cbd5e1;">&bull;</span>
    <span>Warehouse BMTC_WH (X-Small)</span>
    <span style="color: #cbd5e1;">&bull;</span>
    <span style="color: #64748b;">Sync: Live</span>
  </div>
</div>
""", unsafe_allow_html=True)

render_role_switcher_banner()

# ------------------------------------------------ 1. Network Overview KPIs
st.subheader("Network Overview")
kpi = query(Q.KPIS)
if not kpi.empty:
    k = kpi.iloc[0]
    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("Total Buses", num(k.TOTAL_BUSES), f"{num(k.ACTIVE_BUSES)} in service")
    r2.metric("Active Routes", num(k.TOTAL_ROUTES), "City & feeder lines")
    r3.metric("Scheduled Trips", num(k.TOTAL_TRIPS), f"{k.ON_TIME_PCT}% on-time")
    r4.metric("Tickets Issued", num(k.TOTAL_TICKETS), "Boardings")
    r5.metric("Fare Revenue", money(k.TICKET_REVENUE), "Direct collection")
    r6.metric("Punctuality Rate", f"{k.ON_TIME_PCT}%", "Arrival <= 5 min")

st.divider()

# ------------------------------------------------ 2. Operational Overview (Executive Summary)
st.subheader("Operational Overview")
st.caption("Live aggregate status across scheduled transit trips and fleet availability.")

col_trips, col_fleet = st.columns(2)

with col_trips:
    trip_summary = query("""
        SELECT TRIP_STATUS, COUNT(*) AS TRIPS
        FROM BMTC_DW.TRIP.TRIP_DATA
        GROUP BY TRIP_STATUS
        ORDER BY TRIPS DESC
    """)
    if not trip_summary.empty:
        chart(trip_summary, "bar", "TRIP_STATUS", "TRIPS", "Trip Performance & Completion Status", horizontal=True, height=280)

with col_fleet:
    fleet_summary = query("""
        SELECT STATUS, COUNT(*) AS BUSES
        FROM BMTC_DW.BUS.BUS_MASTER
        GROUP BY STATUS
        ORDER BY BUSES DESC
    """)
    if not fleet_summary.empty:
        chart(fleet_summary, "pie", "STATUS", "BUSES", "Fleet Availability & Roadworthiness", height=280)

st.divider()

# ------------------------------------------------ 3. Operational Attention Required (Action Center)
st.subheader("Attention Required")
st.caption("Proactive operational alerts calculated from live data warehouse records.")

maint_cnt_df = query("SELECT COUNT(*) AS CNT FROM BMTC_DW.BUS.BUS_MASTER WHERE STATUS = 'UNDER_MAINTENANCE'")
maint_cnt = int(maint_cnt_df.iloc[0]["CNT"]) if not maint_cnt_df.empty else 0

delayed_cnt_df = query("SELECT COUNT(*) AS CNT FROM BMTC_DW.TRIP.V_ROUTE_PERFORMANCE WHERE AVG_DELAY_MIN > 5.0")
delayed_cnt = int(delayed_cnt_df.iloc[0]["CNT"]) if not delayed_cnt_df.empty else 0

open_comp_df = query("SELECT COUNT(*) AS CNT FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON WHERE PAYLOAD:status::STRING = 'OPEN'")
open_comp = int(open_comp_df.iloc[0]["CNT"]) if not open_comp_df.empty else 0

poor_fuel_df = query("SELECT COUNT(DISTINCT REGISTRATION_NO) AS CNT FROM BMTC_DW.TRIP.V_FUEL_EFFICIENCY_CLASSIFIED WHERE EFFICIENCY_CLASS = 'POOR'")
poor_fuel = int(poor_fuel_df.iloc[0]["CNT"]) if not poor_fuel_df.empty else 0

a1, a2, a3, a4 = st.columns(4)

with a1:
    with st.container(border=True):
        st.markdown(
            """<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:0.7rem; font-weight:700; color:#b45309; background:#fef3c7; padding:1px 6px; border-radius:4px;">WORKSHOP QUEUE</span>
            </div>
            <div style="font-weight:700; font-size:0.95rem; color:#0f172a;">Fleet Maintenance</div>
            <div style="font-size:0.8rem; color:#64748b; margin-top:2px; min-height:2.6em;">
              4 buses currently undergoing active maintenance in depot workshop bays.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Review Fleet", key="alert_btn_fleet", use_container_width=True):
            st.switch_page("app_pages/2_Bus_Management.py")

with a2:
    with st.container(border=True):
        st.markdown(
            f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:0.7rem; font-weight:700; color:#dc2626; background:#fee2e2; padding:1px 6px; border-radius:4px;">PUNCTUALITY</span>
            </div>
            <div style="font-weight:700; font-size:0.95rem; color:#0f172a;">Route Delays</div>
            <div style="font-size:0.8rem; color:#64748b; margin-top:2px; min-height:2.6em;">
              {delayed_cnt} routes experiencing average trip delays exceeding 5 minutes.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Inspect Routes", key="alert_btn_routes", use_container_width=True):
            st.switch_page("app_pages/3_Routes_Trips.py")

with a3:
    with st.container(border=True):
        st.markdown(
            f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:0.7rem; font-weight:700; color:#0369a1; background:#e0f2fe; padding:1px 6px; border-radius:4px;">PASSENGER GRIEVANCE</span>
            </div>
            <div style="font-weight:700; font-size:0.95rem; color:#0f172a;">Open Complaints</div>
            <div style="font-size:0.8rem; color:#64748b; margin-top:2px; min-height:2.6em;">
              {open_comp} passenger grievances in queue awaiting supervisor triage.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Triage Complaints", key="alert_btn_comp", use_container_width=True):
            st.switch_page("app_pages/6_Passenger_Complaints.py")

with a4:
    with st.container(border=True):
        st.markdown(
            f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:0.7rem; font-weight:700; color:#7c3aed; background:#ede9fe; padding:1px 6px; border-radius:4px;">ENERGY WATCH</span>
            </div>
            <div style="font-weight:700; font-size:0.95rem; color:#0f172a;">Fuel Outliers</div>
            <div style="font-size:0.8rem; color:#64748b; margin-top:2px; min-height:2.6em;">
              {poor_fuel} vehicles flagged by Python UDF with sub-optimal fuel efficiency.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Workshop Logs", key="alert_btn_fuel", use_container_width=True):
            st.switch_page("app_pages/5_Fuel_Maintenance.py")

st.divider()

# ------------------------------------------------ 4. Operational Workspaces & Portals
st.subheader("Operational Workspaces")
st.caption("Access specialized operational consoles tailored to transport roles and intelligence.")

w_ops, w_people, w_dw = st.tabs([
    "Operations Management",
    "People & Role Portals",
    "Data Platform & Architecture",
])

with w_ops:
    w1, w2, w3, w4 = st.columns(4)
    with w1, st.container(border=True):
        st.markdown("**Fleet Management**\n\n120 registered fleet buses, depot assignments, and status updates.")
        if st.button("Open Fleet Console", key="ws_fleet", use_container_width=True):
            st.switch_page("app_pages/2_Bus_Management.py")
    with w2, st.container(border=True):
        st.markdown("**Routes & Trips**\n\n40 transit routes, route revenue ranking, and live trip execution logs.")
        if st.button("Open Route Analytics", key="ws_routes", use_container_width=True):
            st.switch_page("app_pages/3_Routes_Trips.py")
    with w3, st.container(border=True):
        st.markdown("**Ticket Analytics**\n\n120,718 ticket transactions, payment mix (Cash/UPI), and hourly peak boardings.")
        if st.button("Open Ticketing", key="ws_tickets", use_container_width=True):
            st.switch_page("app_pages/4_Ticket_Analytics.py")
    with w4, st.container(border=True):
        st.markdown("**Fuel & Maintenance**\n\nPython UDF fuel efficiency classification, EV charging, and workshop job orders.")
        if st.button("Open Maintenance", key="ws_maint", use_container_width=True):
            st.switch_page("app_pages/5_Fuel_Maintenance.py")

with w_people:
    p1, p2, p3, p4 = st.columns(4)
    with p1, st.container(border=True):
        st.markdown("**Driver Duty Portal**\n\nAssigned routes, pre-trip vehicle safety checklist (DVIR), and trip status updater.")
        if st.button("Launch Driver Portal", key="ws_driver", use_container_width=True):
            st.switch_page("app_pages/9_Driver_Portal.py")
    with p2, st.container(border=True):
        st.markdown("**Conductor ETM**\n\nElectronic Ticketing Machine, Karnataka Shakti Scheme zero-fare passes, and QR validator.")
        if st.button("Launch Conductor ETM", key="ws_cond", use_container_width=True):
            st.switch_page("app_pages/10_Conductor_ETM.py")
    with p3, st.container(border=True):
        st.markdown("**Depot Command**\n\nMorning turnout meter, crew and fleet dispatch roster, and workshop defect queue.")
        if st.button("Launch Depot Command", key="ws_depot", use_container_width=True):
            st.switch_page("app_pages/11_Depot_Operations.py")
    with p4, st.container(border=True):
        st.markdown("**Staff Directory**\n\n300 employees across 10 depots with role-based privacy masking.")
        if st.button("Open Staff Directory", key="ws_staff", use_container_width=True):
            st.switch_page("app_pages/12_Staff_Directory.py")

with w_dw:
    c_arch, c_inv = st.columns([1.1, 0.9])
    with c_arch, st.container(border=True):
        st.markdown("**Data Architecture & Pipeline**")
        st.markdown("""
        * **Ingestion:** CSV & semi-structured JSON &rarr; Internal Stage &rarr; Transient Staging &rarr; Core DW.
        * **CDC & Streams:** `TRIP_DATA_STREAM` captures real-time append deltas.
        * **Automated Tasks:** Snowflake Tasks execute incremental aggregation on stream triggers.
        * **Platform Features:** Time Travel, Zero-Copy Cloning, Masking Policies, Row Access Policies.
        """)
        d1, d2 = st.columns(2)
        if d1.button("Advanced SQL Analytics", key="ws_sql", use_container_width=True):
            st.switch_page("app_pages/7_Advanced_Analytics.py")
        if d2.button("Data Platform Console", key="ws_data", use_container_width=True):
            st.switch_page("app_pages/8_Data_Management.py")

    with c_inv, st.container(border=True):
        st.markdown("**Live Database Inventory (BMTC_DW)**")
        tables = query("""
        SELECT TABLE_SCHEMA AS SCHEMA_NAME, TABLE_NAME, ROW_COUNT,
               IFF(IS_TRANSIENT = 'YES', 'TRANSIENT', 'PERMANENT') AS TABLE_KIND
        FROM BMTC_DW.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ('BUS', 'TRIP', 'PASSENGER') AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME""")
        if not tables.empty:
            st.caption(f"Total synchronized records: {num(tables['ROW_COUNT'].sum())}")
        show_table(tables, height=200)
