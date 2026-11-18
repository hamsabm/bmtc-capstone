"""BMTC Operational Crew Login Portal.

Provides separate, dedicated, and strictly authenticated login portals for:
  * Bus Drivers (Duty Schedule, Pre-Trip DVIR Inspection Checklist, Trip Logger)
  * Bus Conductors (Electronic Ticketing Machine - ETM, Shakti Scheme Pink Tickets, Pass Validator)
  * Platform Administrators & Faculty Evaluators (DW Architecture & Analytics Review)
"""
import streamlit as st

from utils.auth import DEMO_ACCOUNTS, get_current_user, login_as, logout, verify_credentials
from utils.ui import page

page("Crew & Operations Authentication", "Secure, credential-verified portal sign-in for BMTC operational staff")

curr = get_current_user()
curr_role = curr.get("role", "Admin")
is_authenticated = (curr_role not in ["Guest", None])

# ------------------------------------------------ Active Session Status Banner
c_info, c_out = st.columns([4.2, 1.8], vertical_alignment="center")
with c_info:
    if is_authenticated:
        badge_bg = "#059669" if curr_role == "Driver" else ("#d97706" if curr_role == "Conductor" else "#1e3a8a")
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
          <span style="font-size: 0.85rem; color: #475569;">Active Session:</span>
          <span style="font-weight: 700; color: #0f172a; font-size: 0.92rem;">{curr.get('name')}</span>
          <span style="background: {badge_bg}; color: #ffffff; padding: 1px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">{curr_role.upper()}</span>
          <span style="font-size: 0.75rem; color: #64748b;">({curr.get('employee_code')}) &bull; Depot: <b>{curr.get('depot_name', 'BMTC')}</b></span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; gap: 10px;">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; display: inline-block;"></span>
          <span style="font-size: 0.85rem; color: #64748b;">Workspace Status:</span>
          <span style="font-weight: 700; color: #475569; font-size: 0.92rem;">Unauthenticated / Locked</span>
          <span style="background: #e2e8f0; color: #475569; padding: 1px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">GUEST</span>
        </div>
        """, unsafe_allow_html=True)

with c_out:
    if is_authenticated:
        if st.button("🚪 Sign Out / Lock Session", key="btn_signout_top", use_container_width=True):
            logout()
            st.rerun()
    else:
        st.caption("Please sign in below to unlock confidential crew portals.")

# ------------------------------------------------ Authorized Credentials Callout
st.markdown("""
<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 8px; padding: 12px 16px; margin: 14px 0 18px 0;">
  <div style="font-weight: 700; font-size: 0.88rem; color: #166534; display: flex; align-items: center; gap: 6px;">
    <span>🛡️</span> Authorized Evaluation & Crew Credentials Roster
  </div>
  <div style="font-size: 0.8rem; color: #15803d; margin-top: 4px; line-height: 1.5;">
    To enforce data confidentiality, arbitrary logins are rejected. Use the verified employee records below:
  </div>
  <div style="display: flex; flex-wrap: wrap; gap: 18px; margin-top: 8px; font-size: 0.78rem; color: #166534;">
    <div style="background: #ffffff; padding: 6px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
      <b>🚌 Driver:</b> Code: <code>EMP00001</code> &bull; PIN: <code>1001</code> <i>(Rekha Reddy)</i>
    </div>
    <div style="background: #ffffff; padding: 6px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
      <b>🎟️ Conductor:</b> Code: <code>EMP00013</code> &bull; PIN: <code>1301</code> <i>(Shwetha Kulkarni)</i>
    </div>
    <div style="background: #ffffff; padding: 6px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
      <b>⚙️ Platform Admin:</b> Code: <code>ADMIN001</code> &bull; Passkey: <code>9999</code>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

col_driver, col_conductor = st.columns(2)

# =====================================================================
# 1. DRIVER LOGIN PORTAL
# =====================================================================
with col_driver:
    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 36px; height: 36px; border-radius: 8px; background: #ecfdf5; border: 1px solid #a7f3d0; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
              🚌
            </div>
            <div>
              <div style="font-weight: 800; font-size: 1.05rem; color: #065f46;">Driver Portal Sign-In</div>
              <div style="font-size: 0.72rem; color: #059669; font-weight: 600;">DUTY &bull; SAFETY DVIR &bull; TRIP LOGGER</div>
            </div>
          </div>
          <span style="font-size: 0.68rem; font-weight: 700; background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; padding: 1px 6px; border-radius: 4px;">CONFIDENTIAL</span>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Confidential driver duty dashboard. View assigned bus routes, conduct 8-point pre-trip DVIR vehicle inspections, and log scheduled trip milestones.")

        with st.form("driver_login_form"):
            driver_code = st.text_input("Driver Employee Code", value="", placeholder="e.g. EMP00001", key="drv_code_input")
            driver_pin = st.text_input("Security PIN", value="", placeholder="Enter 4-digit PIN", type="password", key="drv_pin_input")

            submit_driver = st.form_submit_button("Sign In to Driver Workspace", use_container_width=True, type="primary")
            if submit_driver:
                valid, result = verify_credentials("driver", driver_code, driver_pin)
                if valid:
                    login_as("driver")
                    st.success("✅ Driver identity verified. Launching duty workspace...")
                    try:
                        st.switch_page("app_pages/9_Driver_Portal.py")
                    except Exception:
                        st.rerun()
                else:
                    st.error(f"❌ Access Denied: {result}")

        if curr_role == "Driver":
            st.info("You are authenticated as Driver Rekha Reddy. Operational logs are active.", icon=":material/lock:")
            if st.button("Open Driver Portal Now", key="go_driver_btn", use_container_width=True):
                try:
                    st.switch_page("app_pages/9_Driver_Portal.py")
                except Exception:
                    st.rerun()

# =====================================================================
# 2. CONDUCTOR LOGIN PORTAL
# =====================================================================
with col_conductor:
    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 36px; height: 36px; border-radius: 8px; background: #fffbeb; border: 1px solid #fde68a; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
              🎟️
            </div>
            <div>
              <div style="font-weight: 800; font-size: 1.05rem; color: #92400e;">Conductor ETM Sign-In</div>
              <div style="font-size: 0.72rem; color: #d97706; font-weight: 600;">ETM TERMINAL &bull; SHAKTI SCHEME &bull; CASH</div>
            </div>
          </div>
          <span style="font-size: 0.68rem; font-weight: 700; background: #fffbeb; color: #92400e; border: 1px solid #fde68a; padding: 1px 6px; border-radius: 4px;">CONFIDENTIAL</span>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Confidential conductor ticketing terminal. Issue route distance tickets, dispense zero-fare Shakti pink tickets, validate monthly bus passes, and reconcile shift cash.")

        with st.form("conductor_login_form"):
            conductor_code = st.text_input("Conductor Employee Code", value="", placeholder="e.g. EMP00013", key="cd_code_input")
            conductor_pin = st.text_input("ETM Device PIN", value="", placeholder="Enter 4-digit PIN", type="password", key="cd_pin_input")

            submit_conductor = st.form_submit_button("Sign In to Conductor ETM", use_container_width=True, type="primary")
            if submit_conductor:
                valid, result = verify_credentials("conductor", conductor_code, conductor_pin)
                if valid:
                    login_as("conductor")
                    st.success("✅ Conductor identity verified. Initializing ETM terminal...")
                    try:
                        st.switch_page("app_pages/10_Conductor_ETM.py")
                    except Exception:
                        st.rerun()
                else:
                    st.error(f"❌ Access Denied: {result}")

        if curr_role == "Conductor":
            st.info("You are authenticated as Conductor Shwetha Kulkarni. ETM terminal is active.", icon=":material/lock:")
            if st.button("Open Conductor ETM Now", key="go_conductor_btn", use_container_width=True):
                try:
                    st.switch_page("app_pages/10_Conductor_ETM.py")
                except Exception:
                    st.rerun()

st.divider()

# =====================================================================
# EVALUATOR / FACULTY ACCESS EXPANDER
# =====================================================================
with st.expander("Faculty Evaluation / Central Platform Administration Access", expanded=False):
    st.caption("Instructors, evaluators, and system administrators must provide authorized administrative passkeys to review full data warehouse schemas, analytics dashboards, and cross-depot performance.")
    
    with st.form("admin_login_form"):
        c_ad1, c_ad2 = st.columns(2)
        with c_ad1:
            admin_code = st.text_input("Administrator Employee Code", value="", placeholder="e.g. ADMIN001", key="ad_code_input")
        with c_ad2:
            admin_pin = st.text_input("Platform Security Passkey", value="", placeholder="Enter Admin Passkey", type="password", key="ad_pin_input")
        
        submit_admin = st.form_submit_button("Authenticate Platform Administrator", use_container_width=True, type="primary")
        if submit_admin:
            valid, result = verify_credentials("admin", admin_code, admin_pin)
            if valid:
                login_as("admin")
                st.success("✅ Platform Administrator authenticated. Loading full governance workspace...")
                try:
                    st.switch_page("home.py")
                except Exception:
                    st.rerun()
            else:
                st.error(f"❌ Access Denied: {result}")
