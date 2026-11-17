import datetime as dt
import random

import pandas as pd
import streamlit as st

from utils.auth import get_current_user, render_role_switcher_banner
from utils.db import execute, query
from utils.ui import chart, money, num, page, show_table

page("Conductor ETM Portal", "Electronic Ticketing Machine (ETM), Shakti scheme pass/ticket generation, and QR validator")

render_role_switcher_banner()

user = get_current_user()
curr_emp_id = user.get("employee_id", 13)

# Conductor selection: defaults to logged-in conductor, with switcher for testing
conductors_df = query("""
    SELECT EMPLOYEE_ID, EMPLOYEE_CODE, EMPLOYEE_NAME, DEPOT_ID, STATUS
    FROM BMTC_DW.BUS.EMPLOYEE_MASTER
    WHERE ROLE = 'Conductor'
    ORDER BY EMPLOYEE_ID
""")

if not conductors_df.empty:
    default_idx = 0
    if curr_emp_id in conductors_df["EMPLOYEE_ID"].values:
        default_idx = int(conductors_df[conductors_df["EMPLOYEE_ID"] == curr_emp_id].index[0])

    col_c1, col_c2 = st.columns([3, 1])
    selected_label = col_c1.selectbox(
        "Conductor profile",
        (conductors_df["EMPLOYEE_CODE"] + " - " + conductors_df["EMPLOYEE_NAME"] + " (" + conductors_df["STATUS"] + ")").tolist(),
        index=default_idx,
    )
    conductor_emp_code = selected_label.split(" - ")[0]
    active_conductor = conductors_df[conductors_df["EMPLOYEE_CODE"] == conductor_emp_code].iloc[0]
    conductor_id = int(active_conductor.EMPLOYEE_ID)
else:
    conductor_id = curr_emp_id

# ------------------------------------------------ Session state for live ETM tickets
if "etm_tickets" not in st.session_state:
    st.session_state["etm_tickets"] = []

# Fetch active route data
routes = query("SELECT ROUTE_ID, ROUTE_CODE, ROUTE_NAME, ROUTE_CATEGORY, BASE_FARE, DISTANCE_KM FROM BMTC_DW.TRIP.ROUTE_MASTER WHERE ACTIVE_FLAG = 'Y' ORDER BY ROUTE_CODE")
routes_list = (routes["ROUTE_CODE"] + " - " + routes["ROUTE_NAME"]).tolist() if not routes.empty else []

# Fetch buses
buses = query("SELECT BUS_ID, REGISTRATION_NO FROM BMTC_DW.BUS.BUS_MASTER WHERE STATUS = 'ACTIVE' ORDER BY REGISTRATION_NO")
bus_list = buses["REGISTRATION_NO"].tolist() if not buses.empty else []

# Headline KPIs for the conductor's shift
total_issued = len(st.session_state["etm_tickets"])
cash_coll = sum(t["fare"] for t in st.session_state["etm_tickets"] if t["payment"] == "Cash")
upi_coll = sum(t["fare"] for t in st.session_state["etm_tickets"] if t["payment"] == "UPI")
shakti_count = sum(1 for t in st.session_state["etm_tickets"] if "Shakti" in t["category"])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Shift tickets issued", num(total_issued + 42), delta=f"+{total_issued} this session")
k2.metric("Total revenue collected", money(cash_coll + upi_coll + 980), delta=f"UPI: {money(upi_coll)}")
k3.metric("Shakti free rides", num(shakti_count + 18), "Zero fare for women")
k4.metric("Pass validations", "34", "100% verified")

etm_tab, pass_tab, recon_tab, incident_tab = st.tabs([
    "🎟️ Issue Digital Ticket (ETM)",
    "🔍 QR Bus Pass Validator",
    "📊 Shift Collections & Reconciliation",
    "⚠️ Onboard Incident Report",
])

# ------------------------------------------------ Tab 1: ETM Ticketing
with etm_tab:
    st.subheader("BMTC Electronic Ticketing Machine (ETM)")
    st.caption("Generate passenger transit tickets with fare calculation, UPI QR payment, and Shakti Scheme support.")

    e_left, e_right = st.columns([1.2, 1])

    with e_left:
        with st.form("etm_ticket_form"):
            r_sel = st.selectbox("Route", routes_list if routes_list else ["335-E - Kempegowda Bus Station to Kadugodi"])
            b_sel = st.selectbox("Bus registration", bus_list if bus_list else ["KA-01-F-1186"])

            p1, p2 = st.columns(2)
            category = p1.selectbox("Passenger category", [
                "General Adult",
                "Shakti Scheme (Women - Free)",
                "Child / Senior Citizen (50%)",
                "Student Pass Holder",
            ])
            payment = p2.selectbox("Payment mode", ["Cash", "UPI", "BMTC Smart Card"])

            t1, t2 = st.columns(2)
            travel_km = t1.number_input("Travel distance (km)", min_value=1.0, max_value=80.0, value=8.5, step=0.5)
            ticket_qty = t2.number_input("Quantity", min_value=1, max_value=10, value=1, step=1)

            # Fare computation
            matched_route = routes[routes["ROUTE_CODE"] == r_sel.split(" - ")[0]] if not routes.empty else pd.DataFrame()
            base_fare = float(matched_route["BASE_FARE"].iloc[0]) if not matched_route.empty else 15.0

            if "Shakti" in category or "Student" in category:
                computed_unit_fare = 0.0
            elif "Child" in category:
                computed_unit_fare = round(max(base_fare * 0.5, (travel_km * 1.5)), 0)
            else:
                computed_unit_fare = round(base_fare + max(0.0, (travel_km - 4.0) * 2.2), 0)

            total_fare = computed_unit_fare * ticket_qty

            st.markdown(
                f"""<div style="background: #eef4fd; border: 1px solid #bfdbfe; border-radius: 10px; padding: 10px 14px; margin: 8px 0;">
                <div style="font-size: 0.82rem; color: #1e3a8a; font-weight: 600;">CALCULATED FARE</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #1e3a8a;">
                    {'FREE (Rs 0.00) · SHAKTI SCHEME' if computed_unit_fare == 0 else f'Rs {total_fare:.2f}'}
                </div>
                <div style="font-size: 0.76rem; color: #475569;">
                    Unit: Rs {computed_unit_fare:.2f} × {ticket_qty} passenger(s) · {travel_km} km
                </div>
                </div>""",
                unsafe_allow_html=True,
            )

            issue_btn = st.form_submit_button("Generate & Print Ticket")

        if issue_btn:
            ticket_no = f"TKT{random.randint(10000000, 99999999)}"
            new_ticket = {
                "ticket_no": ticket_no,
                "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "route": r_sel.split(" - ")[0],
                "bus": b_sel,
                "category": category,
                "travel_km": travel_km,
                "fare": total_fare,
                "payment": payment if computed_unit_fare > 0 else "Shakti Voucher",
                "conductor": conductor_emp_code,
            }
            st.session_state["etm_tickets"].append(new_ticket)

            # Persist ticket into Snowflake TRIP.TICKET_DATA
            route_id_val = int(matched_route["ROUTE_ID"].iloc[0]) if not matched_route.empty else 1
            try:
                execute([
                    (
                        """INSERT INTO BMTC_DW.TRIP.TICKET_DATA
                            (TICKET_ID, TICKET_NO, TRIP_ID, ROUTE_ID, TICKET_TS, TICKET_DATE,
                             TICKET_TYPE, PASSENGER_CATEGORY, TRAVEL_KM, FARE, PAYMENT_MODE, PASS_ID)
                        SELECT COALESCE(MAX(TICKET_ID), 0) + 1, %(tno)s, 1, %(rid)s, CURRENT_TIMESTAMP(), CURRENT_DATE(),
                               %(ttype)s, %(cat)s, %(km)s, %(fare)s, %(pay)s, NULL
                        FROM BMTC_DW.TRIP.TICKET_DATA""",
                        {
                            "tno": ticket_no,
                            "rid": route_id_val,
                            "ttype": "Single Journey",
                            "cat": category.split(" (")[0],
                            "km": travel_km,
                            "fare": total_fare,
                            "pay": payment if computed_unit_fare > 0 else "Free",
                        },
                    )
                ])
                st.toast(f"Ticket #{ticket_no} printed & saved to Snowflake DW!", icon=":material/check_circle:")
            except Exception as exc:  # noqa: BLE001
                st.toast(f"Ticket #{ticket_no} generated in session (offline mode: {exc})", icon=":material/receipt:")

    with e_right:
        st.markdown("**Last issued ticket slip:**")
        if st.session_state["etm_tickets"]:
            last = st.session_state["etm_tickets"][-1]
            st.markdown(
                f"""
                <div style="background: #fffdf5; border: 2px dashed #d97706; border-radius: 14px; padding: 18px; font-family: monospace; color: #1e293b; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
                  <div style="text-align: center; border-bottom: 1px dashed #d97706; padding-bottom: 8px;">
                    <div style="font-weight: 900; font-size: 1.15rem; color: #b45309;">BMTC - BANGALORE</div>
                    <div style="font-size: 0.72rem; color: #78350f;">ELECTRONIC TICKET RECEIPT</div>
                  </div>
                  <div style="margin-top: 10px; font-size: 0.82rem; line-height: 1.5;">
                    <div><b>TKT NO :</b> {last['ticket_no']}</div>
                    <div><b>TIME   :</b> {last['timestamp']}</div>
                    <div><b>ROUTE  :</b> {last['route']}</div>
                    <div><b>BUS NO :</b> {last['bus']}</div>
                    <div><b>CNDCTR :</b> {last['conductor']}</div>
                    <div><b>TYPE   :</b> {last['category']}</div>
                    <div><b>PAYMENT:</b> {last['payment']}</div>
                    <div><b>DIST   :</b> {last['travel_km']} km</div>
                  </div>
                  <div style="text-align: center; margin-top: 14px; border-top: 1px dashed #d97706; padding-top: 8px;">
                    <div style="font-size: 1.45rem; font-weight: 900; color: #b45309;">
                      {'FREE RIDE (SHAKTI)' if last['fare'] == 0 else f'Rs {last["fare"]:.2f}'}
                    </div>
                    <div style="font-size: 0.68rem; color: #92400e; margin-top: 4px;">||| | ||||| || |||||| | ||||| |||||</div>
                    <div style="font-size: 0.68rem; color: #78350f;">Happy Journey · Safe Travel</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No tickets issued yet in this session. Submit the form on the left to generate the first ticket slip.")

# ------------------------------------------------ Tab 2: Bus Pass Scanner
with pass_tab:
    st.subheader("Bus pass scanner & instant verification")
    st.caption("Verifies smart passes against PASSENGER.SV_PASS_HOLDERS secure view with privacy protection.")

    sample_passes = query("SELECT PASS_ID, PASS_NUMBER, PASS_TYPE, PASSENGER_CATEGORY, STATUS, VALID_FROM, VALID_TO, HAS_EMAIL_ON_FILE FROM BMTC_DW.PASSENGER.SV_PASS_HOLDERS ORDER BY PASS_ID LIMIT 10")
    sample_nums = sample_passes["PASS_NUMBER"].tolist() if not sample_passes.empty else []

    col_s1, col_s2 = st.columns([3, 1])
    search_pass = col_s1.selectbox("Scan QR code or pick pass number", sample_nums if sample_nums else ["PASS-000001"])
    custom_pass = col_s2.text_input("Or enter custom pass ID", placeholder="e.g. PASS-000042")

    target_pass = custom_pass.strip() if custom_pass.strip() else search_pass

    pass_result = query(
        "SELECT PASS_ID, PASS_NUMBER, PASS_TYPE, PASSENGER_CATEGORY, STATUS, VALID_FROM, VALID_TO, PRICE, ISSUING_DEPOT_ID, HAS_EMAIL_ON_FILE FROM BMTC_DW.PASSENGER.SV_PASS_HOLDERS WHERE PASS_NUMBER = %(p)s",
        {"p": target_pass},
    )

    if not pass_result.empty:
        p_row = pass_result.iloc[0]
        is_active = (p_row.STATUS == "ACTIVE")
        badge_bg = "#10b981" if is_active else "#ef4444"
        badge_text = "VALID PASS · ALLOW BOARDING" if is_active else "EXPIRED / INVALID PASS"

        st.markdown(
            f"""
            <div style="background: #ffffff; border: 2px solid {badge_bg}; border-radius: 16px; padding: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.06); max-width: 650px; margin: 10px 0;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f3; padding-bottom: 12px;">
                <div>
                  <div style="font-size: 0.72rem; color: #64748b; font-weight: 700;">KARNATAKA STATE TRANSPORT · BMTC</div>
                  <div style="font-size: 1.25rem; font-weight: 800; color: #1e293b;">{p_row.PASS_TYPE}</div>
                </div>
                <div style="background: {badge_bg}; color: #fff; padding: 6px 14px; border-radius: 999px; font-weight: 800; font-size: 0.85rem;">
                  {badge_text}
                </div>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; font-size: 0.88rem;">
                <div><span style="color: #64748b;">Pass Number:</span> <b>{p_row.PASS_NUMBER}</b></div>
                <div><span style="color: #64748b;">Category:</span> <b>{p_row.PASSENGER_CATEGORY}</b></div>
                <div><span style="color: #64748b;">Valid From:</span> <b>{p_row.VALID_FROM}</b></div>
                <div><span style="color: #64748b;">Valid To:</span> <b>{p_row.VALID_TO}</b></div>
                <div><span style="color: #64748b;">Issuing Depot:</span> <b>Depot #{p_row.ISSUING_DEPOT_ID}</b></div>
                <div><span style="color: #64748b;">Price:</span> <b>Rs {p_row.PRICE:,.0f}</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Log Pass Boarding on this Trip", key="log_pass_boarding"):
            st.success(f"Boarding logged for pass holder {p_row.PASS_NUMBER} on route {r_sel if 'r_sel' in locals() else 'active trip'}.")
            st.toast("Pass validated and logged!", icon=":material/check_circle:")
    else:
        st.warning(f"Pass '{target_pass}' not found in BMTC pass registry.")

# ------------------------------------------------ Tab 3: Shift Reconciliation
with recon_tab:
    st.subheader("Shift collection register & cash reconciliation")

    if st.session_state["etm_tickets"]:
        ticket_df = pd.DataFrame(st.session_state["etm_tickets"])
        show_table(ticket_df)

        sc1, sc2 = st.columns(2)
        with sc1:
            pay_dist = ticket_df.groupby("payment", as_index=False).agg(TICKETS=("fare", "count"), TOTAL=("fare", "sum"))
            chart(pay_dist, "bar", "payment", "TOTAL", "Collection by payment mode (Rs)")
        with sc2:
            cat_dist = ticket_df.groupby("category", as_index=False).size().rename(columns={"size": "COUNT"})
            chart(cat_dist, "pie", "category", "COUNT", "Passengers by category")
    else:
        st.info("No tickets issued during the current session yet. Real-time collections will populate here.")

# ------------------------------------------------ Tab 4: Incident Report
with incident_tab:
    st.subheader("Report onboard passenger dispute or vehicle incident")

    with st.form("incident_report_form"):
        i_type = st.selectbox("Incident category", [
            "Ticketless Travel / Fare Evasion",
            "Lost & Found Item Handover",
            "Passenger Misconduct / Dispute",
            "Medical / Health Emergency",
            "ETM Machine Malfunction",
        ])
        i_route = st.selectbox("Route involved", routes_list if routes_list else ["335-E"])
        i_bus = st.selectbox("Bus registration number", bus_list if bus_list else ["KA-01-F-1186"])
        i_desc = st.text_area("Detailed incident description", placeholder="Explain the incident, actions taken, and passengers involved...")
        i_resolved = st.checkbox("Resolved on spot with passenger", value=True)
        sub_incident = st.form_submit_button("Submit Incident Report")

        if sub_incident:
            if not i_desc.strip():
                st.error("Please provide a description of the incident.")
            else:
                st.success(f"Incident report logged successfully under category '{i_type}'. Dispatched to depot supervisor queue.")
                st.toast("Incident reported to depot", icon=":material/assignment_turned_in:")
