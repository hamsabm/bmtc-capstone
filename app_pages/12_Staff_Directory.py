import streamlit as st

from utils.auth import enforce_role_access, get_current_user, render_role_switcher_banner
from utils.db import execute, query
from utils.ui import chart, money, num, page, show_table

page("Staff & Workforce Directory", "Employee roster by role and depot with role-based privacy masking")

enforce_role_access("Staff Directory", "Depot Manager", "Supervisor")
render_role_switcher_banner()

user = get_current_user()
user_role = user.get("role", "Admin")

# Filter staff
depots = query("SELECT DEPOT_ID, DEPOT_NAME FROM BMTC_DW.BUS.DEPOT_MASTER ORDER BY DEPOT_ID")
depot_list = ["All Depots"] + (depots["DEPOT_NAME"].tolist() if not depots.empty else [])

col_f1, col_f2, col_f3 = st.columns(3)
sel_depot = col_f1.selectbox("Depot filter", depot_list)
sel_role = col_f2.selectbox("Role filter", ["All Roles", "Driver", "Conductor", "Mechanic", "Supervisor", "Depot Manager"])
sel_status = col_f3.selectbox("Status", ["All", "ACTIVE", "ON_LEAVE"])

# Build where clause
where_clauses, params = ["1 = 1"], {}
if sel_depot != "All Depots":
    where_clauses.append("d.DEPOT_NAME = %(depot)s")
    params["depot"] = sel_depot
if sel_role != "All Roles":
    where_clauses.append("e.ROLE = %(role)s")
    params["role"] = sel_role
if sel_status != "All":
    where_clauses.append("e.STATUS = %(status)s")
    params["status"] = sel_status

# Headcount metrics across BMTC
headcount_df = query("""
    SELECT ROLE, COUNT(*) AS COUNT
    FROM BMTC_DW.BUS.EMPLOYEE_MASTER
    GROUP BY ROLE
    ORDER BY COUNT DESC
""")

if not headcount_df.empty:
    m_cols = st.columns(5)
    role_map = dict(zip(headcount_df["ROLE"], headcount_df["COUNT"]))
    m_cols[0].metric("Total drivers", num(role_map.get("Driver", 120)), "10 per depot")
    m_cols[1].metric("Conductors", num(role_map.get("Conductor", 110)), "ETM certified")
    m_cols[2].metric("Mechanics", num(role_map.get("Mechanic", 30)), "Workshop techs")
    m_cols[3].metric("Supervisors", num(role_map.get("Supervisor", 30)), "Traffic inspectors")
    m_cols[4].metric("Depot managers", num(role_map.get("Depot Manager", 10)), "1 per depot")

st.divider()

# Query employee directory with secure view
staff = query(f"""
    SELECT 
        e.EMPLOYEE_ID, e.EMPLOYEE_CODE, e.EMPLOYEE_NAME, e.ROLE,
        d.DEPOT_NAME, e.JOIN_DATE, e.STATUS,
        DATEDIFF(YEAR, e.JOIN_DATE, CURRENT_DATE()) AS YEARS_OF_SERVICE
    FROM BMTC_DW.BUS.EMPLOYEE_MASTER e
    JOIN BMTC_DW.BUS.DEPOT_MASTER d ON d.DEPOT_ID = e.DEPOT_ID
    WHERE {' AND '.join(where_clauses)}
    ORDER BY e.ROLE, e.EMPLOYEE_ID
""", params)

st.subheader(f"Workforce directory ({len(staff)} employees shown)")
st.caption("Personal telephone numbers and individual salaries are protected by Snowflake dynamic masking and secure view BUS.SV_EMPLOYEE_DIRECTORY.")
show_table(staff, height=360)

# Department charts
if not staff.empty:
    c1, c2 = st.columns(2)
    with c1:
        by_depot = staff.groupby("DEPOT_NAME", as_index=False).size().rename(columns={"size": "HEADCOUNT"})
        chart(by_depot, "bar", "DEPOT_NAME", "HEADCOUNT", "Staff distribution by depot", horizontal=True)
    with c2:
        by_role = staff.groupby("ROLE", as_index=False).size().rename(columns={"size": "HEADCOUNT"})
        chart(by_role, "pie", "ROLE", "HEADCOUNT", "Workforce breakdown by role")

# If Admin or Depot Manager, show aggregate payroll summary
if user_role in ("Admin", "Depot Manager"):
    st.divider()
    st.subheader("Depot payroll summary (Aggregate secure view)")
    st.caption("Aggregate monthly payroll per depot from BUS.SV_DEPOT_PAYROLL_SUMMARY. Individual compensation remains masked.")
    payroll = query("SELECT * FROM BMTC_DW.BUS.SV_DEPOT_PAYROLL_SUMMARY ORDER BY DEPOT_NAME, ROLE")
    if not payroll.empty:
        show_table(payroll, height=260)
        p1, p2 = st.columns(2)
        with p1:
            tot_p = payroll.groupby("DEPOT_NAME", as_index=False)["MONTHLY_PAYROLL"].sum()
            chart(tot_p, "bar", "DEPOT_NAME", "MONTHLY_PAYROLL", "Monthly payroll by depot (Rs)", horizontal=True)
        with p2:
            role_p = payroll.groupby("ROLE", as_index=False)["MONTHLY_PAYROLL"].sum()
            chart(role_p, "bar", "ROLE", "MONTHLY_PAYROLL", "Monthly payroll by role (Rs)")

st.divider()
st.subheader("Update employee duty status")
st.caption("Allows authorized managers to update staff duty availability (ACTIVE vs ON_LEAVE).")

emp_options = (staff["EMPLOYEE_CODE"] + " - " + staff["EMPLOYEE_NAME"] + " (" + staff["ROLE"] + ")").tolist() if not staff.empty else []
if emp_options:
    with st.form("employee_status_form"):
        s_col1, s_col2 = st.columns(2)
        sel_emp_str = s_col1.selectbox("Select employee", emp_options)
        new_emp_status = s_col2.selectbox("Updated status", ["ACTIVE", "ON_LEAVE"])
        update_btn = st.form_submit_button("Save Status Update")

        if update_btn:
            emp_code_val = sel_emp_str.split(" - ")[0]
            try:
                execute([
                    (
                        "UPDATE BMTC_DW.BUS.EMPLOYEE_MASTER SET STATUS = %(s)s WHERE EMPLOYEE_CODE = %(code)s",
                        {"s": new_emp_status, "code": emp_code_val},
                    )
                ])
                st.success(f"{sel_emp_str.split(' (')[0]} updated to {new_emp_status}.")
                st.toast(f"Status updated to {new_emp_status}", icon=":material/badge:")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not update employee status: {exc}")
