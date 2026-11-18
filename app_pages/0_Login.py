"""BMTC Operational Crew Login Portal.

Provides separate, dedicated, and confidential login portals for:
  * Bus Drivers (Duty Schedule, Pre-Trip DVIR Inspection Checklist, Trip Logger)
  * Bus Conductors (Electronic Ticketing Machine - ETM, Shakti Scheme Pink Tickets, Pass Validator)
"""
import streamlit as st

from utils.auth import DEMO_ACCOUNTS, get_current_user, login_as
from utils.ui import page

page("Crew & Operations Authentication", "Secure, confidential portal sign-in for BMTC operational staff")

curr = get_current_user()
curr_role = curr.get("role", "Admin")

# Active session banner
st.markdown(f"""
<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
  <div style="display: flex; align-items: center; gap: 10px;">
    <span style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
    <span style="font-size: 0.88rem; color: #475569;">Active Session:</span>
    <span style="font-weight: 700; color: #0f172a; font-size: 0.95rem;">{curr.get('name')}</span>
    <span style="background: #0284c7; color: #ffffff; padding: 1px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700;">{curr_role.upper()}</span>
    <span style="font-size: 0.78rem; color: #64748b;">({curr.get('employee_code')})</span>
  </div>
  <div style="font-size: 0.78rem; color: #64748b;">
    Base Depot: <b>{curr.get('depot_name', 'BMTC Central')}</b>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="margin-bottom: 18px;">
  <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a;">Select Operational Role Login</div>
  <div style="font-size: 0.85rem; color: #64748b;">All duty assignments, inspection logs, and ticketing collections are strictly confidential to each authenticated crew member.</div>
</div>
""", unsafe_allow_html=True)

col_driver, col_conductor = st.columns(2)

# =====================================================================
# 1. DRIVER LOGIN PORTAL
# =====================================================================
with col_driver:
    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: #ecfdf5; border: 1px solid #a7f3d0; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
            🚌
          </div>
          <div>
            <div style="font-weight: 800; font-size: 1.05rem; color: #065f46;">Driver Portal Sign-In</div>
            <div style="font-size: 0.72rem; color: #059669; font-weight: 600;">DUTY &bull; SAFETY DVIR &bull; TRIP LOGGER</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Confidential driver duty dashboard. View assigned bus routes, conduct 8-point pre-trip DVIR vehicle inspections, and log scheduled trip milestones.")
        
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 12px; margin: 10px 0; font-size: 0.78rem; color: #334155;">
          <b>Assigned Crew Member:</b> Rekha Reddy (EMP00001)<br>
          <b>Depot Assignment:</b> Shanthinagar Depot-01 &bull; 4 Assigned Routes
        </div>
        """, unsafe_allow_html=True)

        with st.form("driver_login_form"):
            driver_code = st.text_input("Driver Employee Code", value="EMP00001", key="drv_code_input")
            driver_pin = st.text_input("Security PIN", value="••••", type="password", key="drv_pin_input")
            
            submit_driver = st.form_submit_button("Sign In to Driver Workspace", use_container_width=True, type="primary")
            if submit_driver:
                login_as("driver")
                st.success("Authenticated as Driver Rekha Reddy. Redirecting to Driver Portal...")
                st.switch_page("app_pages/9_Driver_Portal.py")

        if curr_role == "Driver":
            st.info("You are currently authenticated as Driver. Data is locked to your employee ID.", icon=":material/lock:")
            if st.button("Open Driver Portal Now", key="go_driver_btn", use_container_width=True):
                st.switch_page("app_pages/9_Driver_Portal.py")

# =====================================================================
# 2. CONDUCTOR LOGIN PORTAL
# =====================================================================
with col_conductor:
    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: #fffbeb; border: 1px solid #fde68a; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
            🎟️
          </div>
          <div>
            <div style="font-weight: 800; font-size: 1.05rem; color: #92400e;">Conductor ETM Sign-In</div>
            <div style="font-size: 0.72rem; color: #d97706; font-weight: 600;">ETM TERMINAL &bull; SHAKTI SCHEME &bull; PASSES</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Confidential conductor ticketing terminal. Issue route distance tickets, dispense zero-fare Shakti pink tickets, validate monthly bus passes, and reconcile shift cash.")
        
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 12px; margin: 10px 0; font-size: 0.78rem; color: #334155;">
          <b>Assigned Crew Member:</b> Shwetha Kulkarni (EMP00013)<br>
          <b>Depot Assignment:</b> Shanthinagar Depot-01 &bull; Terminal #ETM-042
        </div>
        """, unsafe_allow_html=True)

        with st.form("conductor_login_form"):
            conductor_code = st.text_input("Conductor Employee Code", value="EMP00013", key="cd_code_input")
            conductor_pin = st.text_input("ETM Device PIN", value="••••", type="password", key="cd_pin_input")
            
            submit_conductor = st.form_submit_button("Sign In to Conductor ETM", use_container_width=True, type="primary")
            if submit_conductor:
                login_as("conductor")
                st.success("Authenticated as Conductor Shwetha Kulkarni. Redirecting to ETM Terminal...")
                st.switch_page("app_pages/10_Conductor_ETM.py")

        if curr_role == "Conductor":
            st.info("You are currently authenticated as Conductor. Data is locked to your employee ID.", icon=":material/lock:")
            if st.button("Open Conductor ETM Now", key="go_conductor_btn", use_container_width=True):
                st.switch_page("app_pages/10_Conductor_ETM.py")

st.divider()

# =====================================================================
# EVALUATOR / FACULTY ACCESS EXPANDER
# =====================================================================
with st.expander("Faculty Evaluation / Central Platform Administration Access", expanded=False):
    st.caption("Instructors, evaluators, and system administrators can switch into Platform Admin mode to review all data warehouse schemas, analytics dashboards, and cross-depot performance.")
    c_ad1, c_ad2 = st.columns([2, 4])
    with c_ad1:
        if st.button("Sign In as Platform Administrator", key="login_admin_btn", use_container_width=True):
            login_as("admin")
            st.success("Authenticated as Central Platform Admin.")
            st.switch_page("home.py")
    with c_ad2:
        st.markdown("""
        <div style="font-size: 0.8rem; color: #64748b; padding-top: 6px;">
          Full access role allows viewing all 120 buses, 40 routes, 3,946 trips, Power BI datasets, and data governance console.
        </div>
        """, unsafe_allow_html=True)
