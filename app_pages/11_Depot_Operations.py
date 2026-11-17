import datetime as dt

import pandas as pd
import streamlit as st

from utils import queries as Q
from utils.auth import enforce_role_access, get_current_user, render_role_switcher_banner
from utils.db import execute, query
from utils.ui import chart, money, num, page, show_table

page("Depot Operations Command", "Depot morning turnout, crew & fleet dispatch, and depot-level KPI monitoring")

enforce_role_access("Depot Command", "Depot Manager", "Supervisor")
render_role_switcher_banner()

user = get_current_user()
curr_role = user.get("role", "Admin")
curr_depot_id = user.get("depot_id", 1)

# Fetch depots
depots = query("SELECT DEPOT_ID, DEPOT_CODE, DEPOT_NAME, ZONE, ADDRESS, BUS_CAPACITY FROM BMTC_DW.BUS.DEPOT_MASTER ORDER BY DEPOT_ID")
depot_names = depots["DEPOT_NAME"].tolist() if not depots.empty else ["Shanthinagar Depot"]

default_depot_idx = 0
if curr_depot_id and not depots.empty and curr_depot_id in depots["DEPOT_ID"].values:
    default_depot_idx = int(depots[depots["DEPOT_ID"] == curr_depot_id].index[0])

sel_depot = st.selectbox(
    "Active depot command center",
    depot_names,
    index=default_depot_idx,
    help="Select a BMTC depot to inspect turnout, crew assignments, and fleet readiness",
)

matched_depot = depots[depots["DEPOT_NAME"] == sel_depot].iloc[0] if not depots.empty else pd.Series()
depot_id = int(matched_depot.DEPOT_ID) if not matched_depot.empty else 1
zone_name = matched_depot.ZONE if not matched_depot.empty else "South Zone"

# ------------------------------------------------ Depot headline metrics
depot_buses = query(f"""
    SELECT 
        BUS_ID, REGISTRATION_NO, BUS_TYPE, FUEL_TYPE, STATUS, 
        MANUFACTURE_YEAR, SEATING_CAPACITY
    FROM BMTC_DW.BUS.BUS_MASTER
    WHERE DEPOT_ID = {depot_id}
    ORDER BY REGISTRATION_NO
""")

total_fleet = len(depot_buses)
active_fleet = (depot_buses["STATUS"] == "ACTIVE").sum() if not depot_buses.empty else 0
maint_fleet = (depot_buses["STATUS"] == "UNDER_MAINTENANCE").sum() if not depot_buses.empty else 0
turnout_pct = round(100.0 * active_fleet / max(total_fleet, 1), 1)

d1, d2, d3, d4 = st.columns(4)
d1.metric("Depot fleet size", num(total_fleet), f"Zone: {zone_name}")
d2.metric("Morning turnout", f"{turnout_pct}%", f"{active_fleet} active buses on road")
d3.metric("Under maintenance", num(maint_fleet), "In depot workshop", delta_color="inverse")
d4.metric("Assigned workforce", num(query(f"SELECT COUNT(*) AS CNT FROM BMTC_DW.BUS.EMPLOYEE_MASTER WHERE DEPOT_ID = {depot_id}").iloc[0, 0]), "Drivers, Conductors, Techs")

turnout_tab, dispatch_tab, maint_tab, energy_tab = st.tabs([
    "🚌 Morning Turnout & Bus Readiness",
    "🧑‍✈️ Crew & Fleet Dispatch Roster",
    "🔧 Workshop & Defect Queue",
    "⛽ Depot Fuel & EV Efficiency",
])

# ------------------------------------------------ Tab 1: Morning Turnout
with turnout_tab:
    st.subheader(f"Fleet readiness at {sel_depot}")
    st.caption("Real-time readiness audit across assigned bus fleet.")

    if not depot_buses.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            status_summary = depot_buses.groupby("STATUS", as_index=False).size().rename(columns={"size": "BUSES"})
            chart(status_summary, "pie", "STATUS", "BUSES", "Fleet status breakdown")
        with c2:
            type_summary = depot_buses.groupby("BUS_TYPE", as_index=False).size().rename(columns={"size": "BUSES"})
            chart(type_summary, "bar", "BUS_TYPE", "BUSES", "Buses by vehicle type", horizontal=True)

        st.markdown("**Bus roster at depot:**")
        show_table(depot_buses, height=280)
    else:
        st.info("No buses currently registered to this depot.")

# ------------------------------------------------ Tab 2: Crew & Fleet Dispatch
with dispatch_tab:
    st.subheader("Dispatch crew & vehicle on route")
    st.caption("Assign an active driver, conductor, and roadworthy bus to an operational route.")

    # Fetch available staff and buses for this depot
    available_drivers = query(f"SELECT EMPLOYEE_ID, EMPLOYEE_CODE, EMPLOYEE_NAME FROM BMTC_DW.BUS.EMPLOYEE_MASTER WHERE DEPOT_ID = {depot_id} AND ROLE = 'Driver' AND STATUS = 'ACTIVE' ORDER BY EMPLOYEE_NAME")
    available_conductors = query(f"SELECT EMPLOYEE_ID, EMPLOYEE_CODE, EMPLOYEE_NAME FROM BMTC_DW.BUS.EMPLOYEE_MASTER WHERE DEPOT_ID = {depot_id} AND ROLE = 'Conductor' AND STATUS = 'ACTIVE' ORDER BY EMPLOYEE_NAME")
    active_buses = query(f"SELECT BUS_ID, REGISTRATION_NO, BUS_TYPE FROM BMTC_DW.BUS.BUS_MASTER WHERE DEPOT_ID = {depot_id} AND STATUS = 'ACTIVE' ORDER BY REGISTRATION_NO")
    active_routes = query(f"SELECT ROUTE_ID, ROUTE_CODE, ROUTE_NAME, DISTANCE_KM FROM BMTC_DW.TRIP.ROUTE_MASTER WHERE DEPOT_ID = {depot_id} AND ACTIVE_FLAG = 'Y' ORDER BY ROUTE_CODE")
    if active_routes.empty:
        active_routes = query("SELECT ROUTE_ID, ROUTE_CODE, ROUTE_NAME, DISTANCE_KM FROM BMTC_DW.TRIP.ROUTE_MASTER WHERE ACTIVE_FLAG = 'Y' ORDER BY ROUTE_CODE LIMIT 15")

    with st.form("dispatch_form"):
        col_f1, col_f2 = st.columns(2)
        driver_choices = (available_drivers["EMPLOYEE_CODE"] + " - " + available_drivers["EMPLOYEE_NAME"]).tolist() if not available_drivers.empty else ["EMP00001 - Rekha Reddy"]
        conductor_choices = (available_conductors["EMPLOYEE_CODE"] + " - " + available_conductors["EMPLOYEE_NAME"]).tolist() if not available_conductors.empty else ["EMP00013 - Shwetha Kulkarni"]
        sel_drv = col_f1.selectbox("Assigned driver", driver_choices)
        sel_cnd = col_f2.selectbox("Assigned conductor", conductor_choices)

        col_f3, col_f4 = st.columns(2)
        bus_choices = (active_buses["REGISTRATION_NO"] + " (" + active_buses["BUS_TYPE"] + ")").tolist() if not active_buses.empty else ["KA-01-F-1186 (Diesel Non-AC)"]
        route_choices = (active_routes["ROUTE_CODE"] + " - " + active_routes["ROUTE_NAME"]).tolist() if not active_routes.empty else ["335-E - KBS to Kadugodi"]
        sel_bus = col_f3.selectbox("Assigned bus", bus_choices)
        sel_rt = col_f4.selectbox("Operational route", route_choices)

        col_f5, col_f6 = st.columns(2)
        dep_time = col_f5.time_input("Scheduled departure", dt.time(6, 30))
        dist_km = col_f6.number_input("Trip scheduled distance (km)", min_value=5.0, max_value=80.0, value=22.5, step=0.5)

        dispatch_btn = st.form_submit_button("Dispatch Bus & Crew to Service")

    if dispatch_btn:
        reg_no = sel_bus.split(" (")[0]
        drv_name = sel_drv.split(" - ")[1]
        cnd_name = sel_cnd.split(" - ")[1]
        rt_code = sel_rt.split(" - ")[0]

        try:
            # Map selected labels to IDs
            bus_row = active_buses[active_buses["REGISTRATION_NO"] == reg_no]
            bus_id_val = int(bus_row["BUS_ID"].iloc[0]) if not bus_row.empty else 1

            drv_code = sel_drv.split(" - ")[0]
            drv_row = available_drivers[available_drivers["EMPLOYEE_CODE"] == drv_code]
            drv_id_val = int(drv_row["EMPLOYEE_ID"].iloc[0]) if not drv_row.empty else 1

            cnd_code = sel_cnd.split(" - ")[0]
            cnd_row = available_conductors[available_conductors["EMPLOYEE_CODE"] == cnd_code]
            cnd_id_val = int(cnd_row["EMPLOYEE_ID"].iloc[0]) if not cnd_row.empty else 13

            rt_row = active_routes[active_routes["ROUTE_CODE"] == rt_code]
            rt_id_val = int(rt_row["ROUTE_ID"].iloc[0]) if not rt_row.empty else 1

            execute([
                (
                    """INSERT INTO BMTC_DW.TRIP.TRIP_DATA
                        (TRIP_ID, BUS_ID, ROUTE_ID, DRIVER_ID, CONDUCTOR_ID, TRIP_DATE,
                         SCHEDULED_START, ACTUAL_START, ACTUAL_END, DELAY_MINUTES, PASSENGER_COUNT,
                         DISTANCE_KM, TRIP_STATUS)
                    SELECT COALESCE(MAX(TRIP_ID), 0) + 1, %(b)s, %(r)s, %(d)s, %(c)s, CURRENT_DATE(),
                           CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL, 0, 0, %(km)s, 'SCHEDULED'
                    FROM BMTC_DW.TRIP.TRIP_DATA""",
                    {"b": bus_id_val, "r": rt_id_val, "d": drv_id_val, "c": cnd_id_val, "km": dist_km},
                )
            ])
            st.success(f"Trip successfully dispatched! Bus {reg_no} on Route {rt_code} with Driver {drv_name} & Conductor {cnd_name}.")
            st.toast(f"Dispatched {reg_no} to {rt_code}", icon=":material/departure_board:")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Dispatch failed: {exc}")

    st.markdown("**Recent depot dispatches & operational trips:**")
    depot_trips = query(f"""
        SELECT 
            t.TRIP_ID, t.TRIP_DATE,
            TO_CHAR(t.SCHEDULED_START, 'HH24:MI') AS DEPARTURE,
            r.ROUTE_CODE, b.REGISTRATION_NO,
            ed.EMPLOYEE_NAME AS DRIVER,
            ec.EMPLOYEE_NAME AS CONDUCTOR,
            t.TRIP_STATUS, t.PASSENGER_COUNT, t.DELAY_MINUTES
        FROM BMTC_DW.TRIP.TRIP_DATA t
        JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
        JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = t.BUS_ID
        JOIN BMTC_DW.BUS.EMPLOYEE_MASTER ed ON ed.EMPLOYEE_ID = t.DRIVER_ID
        JOIN BMTC_DW.BUS.EMPLOYEE_MASTER ec ON ec.EMPLOYEE_ID = t.CONDUCTOR_ID
        WHERE b.DEPOT_ID = {depot_id}
        ORDER BY t.TRIP_DATE DESC, t.SCHEDULED_START DESC
        LIMIT 20
    """)
    show_table(depot_trips, height=280)

# ------------------------------------------------ Tab 3: Workshop Status
with maint_tab:
    st.subheader(f"Depot workshop queue ({sel_depot})")
    depot_maint = query(f"""
        SELECT 
            m.MAINTENANCE_ID, m.MAINTENANCE_DATE, b.REGISTRATION_NO, b.BUS_TYPE,
            m.MAINTENANCE_TYPE, m.DESCRIPTION, m.SEVERITY, m.TOTAL_COST,
            m.DOWNTIME_HOURS, m.STATUS, em.EMPLOYEE_NAME AS MECHANIC
        FROM BMTC_DW.TRIP.MAINTENANCE_LOG m
        JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = m.BUS_ID
        LEFT JOIN BMTC_DW.BUS.EMPLOYEE_MASTER em ON em.EMPLOYEE_ID = m.MECHANIC_ID
        WHERE b.DEPOT_ID = {depot_id}
        ORDER BY m.MAINTENANCE_DATE DESC
        LIMIT 25
    """)
    if not depot_maint.empty:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Workshop jobs", num(len(depot_maint)))
        mc2.metric("Cumulative repair cost", money(depot_maint["TOTAL_COST"].sum()))
        mc3.metric("Total downtime", f"{depot_maint['DOWNTIME_HOURS'].sum():,.0f} hours")
        show_table(depot_maint, height=300)
    else:
        st.info("No active maintenance records logged for this depot.")

# ------------------------------------------------ Tab 4: Energy & Efficiency
with energy_tab:
    st.subheader("Depot energy consumption & fuel cost")
    depot_fuel = query(f"""
        SELECT 
            f.FUEL_DATE, b.REGISTRATION_NO, b.BUS_TYPE, f.FUEL_TYPE,
            f.QUANTITY, f.UNIT, f.TOTAL_COST, f.KM_SINCE_LAST_FILL,
            ROUND(f.KM_SINCE_LAST_FILL / NULLIF(f.QUANTITY, 0), 2) AS EFFICIENCY
        FROM BMTC_DW.TRIP.FUEL_LOG f
        JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = f.BUS_ID
        WHERE b.DEPOT_ID = {depot_id}
        ORDER BY f.FUEL_DATE DESC
        LIMIT 30
    """)
    if not depot_fuel.empty:
        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("Fuel events logged", num(len(depot_fuel)))
        fc2.metric("Total energy expense", money(depot_fuel["TOTAL_COST"].sum()))
        fc3.metric("Average efficiency", f"{depot_fuel['EFFICIENCY'].mean():.2f} km/unit")
        show_table(depot_fuel, height=300)
    else:
        st.info("No fuel records found for buses assigned to this depot.")
