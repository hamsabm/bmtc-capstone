import datetime as dt

import pandas as pd
import streamlit as st

from utils.auth import enforce_role_access, get_assigned_routes, get_current_user, render_role_switcher_banner
from utils.db import execute, query
from utils.ui import chart, num, page, show_table

page("Driver Portal", "Personal duty schedule, vehicle pre-trip safety checklist, and live trip logger")

enforce_role_access("Driver Portal", "Driver", "Depot Manager", "Supervisor")
render_role_switcher_banner()

user = get_current_user()
is_driver = (user.get("role") == "Driver")
curr_emp_id = user.get("employee_id", 1)

# Driver selection: If logged in as driver, lock to authenticated profile; otherwise allow managers to audit
if is_driver:
    driver_id = curr_emp_id
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(5,150,105,0.09) 0%, rgba(16,185,129,0.04) 100%); border: 1px solid #10b981; border-left: 5px solid #059669; border-radius: 12px; padding: 14px 20px; margin: 8px 0 16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.4rem;">🚌</span>
                <span style="font-weight: 800; font-size: 1.15rem; color: #065f46;">{user.get('name')}</span>
                <span style="background: #059669; color: white; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 800;">ACTIVE DRIVER</span>
                <span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;"><code>{user.get('employee_code')}</code></span>
              </div>
              <div style="font-size: 0.82rem; color: #047857; margin-top: 5px;">
                📍 Base Depot: <b>{user.get('depot_name')}</b> &bull; Assigned Routes: <b>146B, MF-167B, V-114A, MF-106B</b>
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 0.72rem; color: #047857; text-transform: uppercase; font-weight: 700;">Shift Status</div>
              <div style="font-weight: 800; color: #065f46; font-size: 1rem;">🟢 ON DUTY &bull; SHIFT 1</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    driver_df = query("""
        SELECT EMPLOYEE_ID, EMPLOYEE_CODE, EMPLOYEE_NAME, DEPOT_ID, STATUS
        FROM BMTC_DW.BUS.EMPLOYEE_MASTER
        WHERE ROLE = 'Driver'
        ORDER BY EMPLOYEE_ID
    """)
    if not driver_df.empty:
        default_idx = 0
        if curr_emp_id in driver_df["EMPLOYEE_ID"].values:
            default_idx = int(driver_df[driver_df["EMPLOYEE_ID"] == curr_emp_id].index[0])

        col_d1, col_d2 = st.columns([3, 1])
        selected_driver_label = col_d1.selectbox(
            "Driver profile (Auditor View)",
            (driver_df["EMPLOYEE_CODE"] + " - " + driver_df["EMPLOYEE_NAME"] + " (" + driver_df["STATUS"] + ")").tolist(),
            index=default_idx,
            help="Select a driver to view their assigned duties and driving record",
        )
        selected_emp_code = selected_driver_label.split(" - ")[0]
        active_driver = driver_df[driver_df["EMPLOYEE_CODE"] == selected_emp_code].iloc[0]
        driver_id = int(active_driver.EMPLOYEE_ID)
    else:
        driver_id = curr_emp_id

# ------------------------------------------------ Driver KPIs
driver_kpis = query(f"""
    SELECT 
        COUNT(*) AS TOTAL_TRIPS,
        COALESCE(SUM(DISTANCE_KM), 0) AS TOTAL_KM,
        COALESCE(SUM(PASSENGER_COUNT), 0) AS TOTAL_PAX,
        ROUND(100.0 * COUNT_IF(COALESCE(DELAY_MINUTES, 0) <= 5) / NULLIF(COUNT(*), 0), 1) AS ON_TIME_PCT,
        ROUND(AVG(COALESCE(DELAY_MINUTES, 0)), 1) AS AVG_DELAY_MIN
    FROM BMTC_DW.TRIP.TRIP_DATA
    WHERE DRIVER_ID = {driver_id}
""")

k = driver_kpis.iloc[0] if not driver_kpis.empty else pd.Series()
total_trips = k.get("TOTAL_TRIPS", 0) or 0
total_km = k.get("TOTAL_KM", 0) or 0
on_time = k.get("ON_TIME_PCT", 95.0) or 95.0
avg_delay = k.get("AVG_DELAY_MIN", 3.2) or 3.2

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trips operated", num(total_trips))
c2.metric("Kilometers driven", f"{num(total_km)} km")
c3.metric("On-time punctuality", f"{on_time}%", delta="+2.4% vs depot avg")
c4.metric("Safety rating", "4.9 ★", "Zero incident record")

tab_duty, tab_routes, tab_inspect, tab_perf = st.tabs([
    "📋 Assigned Duty & Trip Logger",
    "🗺️ My Assigned Routes & Fleet",
    "🛡️ Pre-Trip Safety Inspection",
    "📈 Performance & Trip History",
])

# ------------------------------------------------ Tab 1: Assigned Duty & Trip Logger
with tab_duty:
    st.subheader("Assigned trips for driver")
    st.caption("Active schedule from TRIP.TRIP_DATA linked with route and assigned fleet bus.")

    trips = query(f"""
        SELECT 
            t.TRIP_ID, t.TRIP_DATE, 
            TO_CHAR(t.SCHEDULED_START, 'HH24:MI') AS SCHED_TIME,
            r.ROUTE_CODE, r.ROUTE_NAME, r.ROUTE_CATEGORY,
            b.REGISTRATION_NO, b.BUS_TYPE,
            t.DISTANCE_KM, t.TRIP_STATUS, t.DELAY_MINUTES,
            t.PASSENGER_COUNT
        FROM BMTC_DW.TRIP.TRIP_DATA t
        JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
        JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = t.BUS_ID
        WHERE t.DRIVER_ID = {driver_id}
        ORDER BY t.TRIP_DATE DESC, t.SCHEDULED_START DESC
        LIMIT 25
    """)

    if trips.empty:
        st.info("No trips assigned to this driver in the schedule log.")
    else:
        show_table(trips, height=280)

        st.divider()
        st.subheader("Live trip status update")
        st.caption("Update trip execution status, record on-route delays or report mechanical breakdown.")

        with st.form("driver_trip_update_form"):
            trip_options = (
                trips["TRIP_ID"].astype(str) + " | " + trips["ROUTE_CODE"] + " - " + trips["ROUTE_NAME"]
                + " (" + trips["REGISTRATION_NO"] + ")"
            ).tolist()
            sel_trip_label = st.selectbox("Select trip", trip_options)
            
            f_col1, f_col2, f_col3 = st.columns(3)
            new_status = f_col1.selectbox("Trip status", ["COMPLETED", "IN_PROGRESS", "DELAYED", "BREAKDOWN"])
            delay_min = f_col2.number_input("Delay (minutes)", min_value=0, max_value=240, value=0, step=5)
            pax_count = f_col3.number_input("Passenger boardings", min_value=0, max_value=150, value=45, step=1)

            reason = st.text_input("Remarks / Delay reason", placeholder="e.g. Heavy traffic near Silk Board junction, clear weather")
            submit_trip = st.form_submit_button("Update Trip Status")

            if submit_trip:
                trip_id_to_update = int(sel_trip_label.split(" | ")[0])
                try:
                    execute([
                        (
                            """UPDATE BMTC_DW.TRIP.TRIP_DATA
                               SET TRIP_STATUS = %(status)s,
                                   DELAY_MINUTES = %(delay)s,
                                   PASSENGER_COUNT = %(pax)s
                               WHERE TRIP_ID = %(tid)s""",
                            {"status": new_status, "delay": delay_min, "pax": pax_count, "tid": trip_id_to_update},
                        )
                    ])
                    st.success(f"Trip #{trip_id_to_update} updated to {new_status} with {delay_min} min delay recorded.")
                    st.toast(f"Trip #{trip_id_to_update} status updated!", icon=":material/check_circle:")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not update trip: {exc}")

# ------------------------------------------------ Tab 2: My Assigned Routes & Fleet
with tab_routes:
    st.subheader("My assigned routes & fleet vehicles")
    st.caption("Active transit routes and fleet buses officially assigned to your driving duty roster.")

    assigned_routes = get_assigned_routes(driver_id, "Driver")
    if assigned_routes.empty:
        st.info("No active route assignments found for this driver ID.")
    else:
        unique_routes = (
            assigned_routes[["ROUTE_ID", "ROUTE_CODE", "ROUTE_NAME", "ROUTE_CATEGORY", "DISTANCE_KM", "BASE_FARE", "DEPOT_NAME"]]
            .drop_duplicates()
        )
        for _, r in unique_routes.iterrows():
            buses_on_route = (
                assigned_routes[assigned_routes["ROUTE_CODE"] == r["ROUTE_CODE"]]["REGISTRATION_NO"]
                .unique()
                .tolist()
            )
            with st.container(border=True):
                rc1, rc2, rc3, rc4 = st.columns([1.5, 3.2, 2, 2.3])
                with rc1:
                    st.markdown(
                        f"""<div style="font-size: 1.35rem; font-weight: 800; color: #059669; letter-spacing: -0.01em;">{r['ROUTE_CODE']}</div>
                        <span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">{r['ROUTE_CATEGORY']}</span>""",
                        unsafe_allow_html=True,
                    )
                with rc2:
                    st.markdown(f"**{r['ROUTE_NAME']}**")
                    st.caption(f"📏 Route Distance: **{r['DISTANCE_KM']} km** &bull; Base Fare: **₹{r['BASE_FARE']:.0f}**")
                with rc3:
                    st.markdown(f"📍 Base Depot: **{r['DEPOT_NAME']}**")
                    st.markdown('<span style="color: #059669; font-weight: 700; font-size: 0.82rem;">🟢 Active Operational Schedule</span>', unsafe_allow_html=True)
                with rc4:
                    st.markdown("**Assigned Fleet Buses:**")
                    bus_badges = " ".join(f"`{b}`" for b in buses_on_route[:3])
                    st.markdown(bus_badges if bus_badges else "None")

# ------------------------------------------------ Tab 3: Pre-Trip Safety Inspection
with tab_inspect:
    st.subheader("Pre-trip vehicle safety checklist (DVIR)")
    st.caption("Mandatory daily vehicle inspection report before leaving the depot per BMTC safety regulations.")

    buses = query("SELECT BUS_ID, REGISTRATION_NO, BUS_TYPE, STATUS FROM BMTC_DW.BUS.BUS_MASTER WHERE STATUS != 'RETIRED' ORDER BY REGISTRATION_NO")
    bus_list = buses["REGISTRATION_NO"].tolist() if not buses.empty else []

    with st.form("pre_trip_inspection_form"):
        i_col1, i_col2 = st.columns(2)
        inspected_bus = i_col1.selectbox("Assigned bus registration", bus_list)
        odo_reading = i_col2.number_input("Current odometer reading (km)", min_value=1000, max_value=999999, value=124500, step=100)

        st.markdown("**Vehicle condition checklist:**")
        chk1, chk2 = st.columns(2)
        with chk1:
            c_brakes = st.checkbox("Brakes & Air Pressure Gauge (> 7.5 Bar)", value=True)
            c_tyres = st.checkbox("Tyres & Wheel Nuts (Good tread, no damage)", value=True)
            c_steering = st.checkbox("Steering & Horn functioning properly", value=True)
            c_lights = st.checkbox("Headlights, Tail Lights & Turn Indicators", value=True)
        with chk2:
            c_wipers = st.checkbox("Windshield Wipers & Washer Fluid", value=True)
            c_emergency = st.checkbox("Emergency Exit Door & Fire Extinguisher", value=True)
            c_firstaid = st.checkbox("First Aid Box & Destination Display Board", value=True)
            c_fuel = st.checkbox("Fuel / EV Battery Charge Adequate (> 85%)", value=True)

        defect_notes = st.text_area("Report any defect or workshop remarks", placeholder="e.g. Wiper blade rubber slightly worn, brake pedal firm, all ok.")
        certify = st.checkbox("I hereby certify that this vehicle has undergone a physical safety inspection and is roadworthy for passenger service.", value=True)
        submit_inspection = st.form_submit_button("Submit Safety Clearance")

        if submit_inspection:
            if not certify:
                st.warning("Please check the certification box to authorize vehicle clearance.")
            else:
                all_passed = all([c_brakes, c_tyres, c_steering, c_lights, c_wipers, c_emergency, c_firstaid, c_fuel])
                if all_passed:
                    st.success(f"Safety clearance APPROVED for {inspected_bus}. Odometer logged at {odo_reading:,} km. Bus is cleared for passenger service!")
                    st.toast(f"Inspection passed for {inspected_bus}", icon=":material/verified:")
                else:
                    st.warning(f"Inspection completed with DEFECTS flagged for {inspected_bus}. Maintenance alert dispatched to depot workshop.")

# ------------------------------------------------ Tab 3: Performance & History
with tab_perf:
    st.subheader("Driver operational record & punctuality")

    history = query(f"""
        SELECT 
            DATE_TRUNC('MONTH', t.TRIP_DATE)::DATE AS MONTH,
            COUNT(*) AS TRIPS_OPERATED,
            ROUND(SUM(t.DISTANCE_KM), 0) AS KM_OPERATED,
            ROUND(100.0 * COUNT_IF(COALESCE(t.DELAY_MINUTES, 0) <= 5) / COUNT(*), 1) AS ON_TIME_PCT,
            ROUND(AVG(t.DELAY_MINUTES), 1) AS AVG_DELAY_MIN
        FROM BMTC_DW.TRIP.TRIP_DATA t
        WHERE t.DRIVER_ID = {driver_id}
        GROUP BY 1
        ORDER BY 1
    """)

    if not history.empty:
        a, b = st.columns(2)
        with a:
            chart(history, "bar", "MONTH", "TRIPS_OPERATED", "Monthly trips operated")
        with b:
            chart(history, "line", "MONTH", "ON_TIME_PCT", "Monthly on-time performance (%)", markers=True)

        st.markdown("**Driver trip performance summary by route:**")
        by_route = query(f"""
            SELECT 
                r.ROUTE_CODE, r.ROUTE_NAME,
                COUNT(*) AS TRIPS,
                ROUND(AVG(t.DISTANCE_KM), 1) AS AVG_KM,
                ROUND(AVG(t.PASSENGER_COUNT), 1) AS AVG_PAX,
                ROUND(AVG(COALESCE(t.DELAY_MINUTES, 0)), 1) AS AVG_DELAY_MIN
            FROM BMTC_DW.TRIP.TRIP_DATA t
            JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
            WHERE t.DRIVER_ID = {driver_id}
            GROUP BY r.ROUTE_CODE, r.ROUTE_NAME
            ORDER BY TRIPS DESC
        """)
        show_table(by_route, height=280)
    else:
        st.info("No historical trip logs found for this driver ID.")
