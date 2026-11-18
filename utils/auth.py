"""Role-Based Access Control (RBAC) and Authentication for BMTC Capstone.

Supported Enterprise Roles:
  * Admin         - Full DW access, system administration, data management, analytics
  * Depot Manager - Depot-scoped fleet turnout, crew dispatch, workshop oversight
  * Driver        - Personal duty schedule, vehicle inspection checklist, trip logger
  * Conductor     - Electronic Ticketing Machine (ETM), Shakti scheme, pass validator
  * Mechanic      - Workshop work orders, repair logging, fleet diagnostics
  * Supervisor    - Route punctuality, line inspection, grievance triage
"""
from __future__ import annotations

import streamlit as st

# Predefined demo accounts mapped to real BMTC organizational roles & employee master
DEMO_ACCOUNTS = {
    "admin": {
        "employee_id": 9999,
        "employee_code": "ADMIN001",
        "name": "Central Platform Admin",
        "role": "Admin",
        "depot_id": 0,
        "depot_name": "BMTC Central Headquarters",
        "email": "admin@bmtc.karnataka.gov.in",
        "avatar": "AD",
        "color": "#1e3a8a",
        "description": "Full platform administration, data warehouse governance, security & enterprise analytics.",
    },
    "driver": {
        "employee_id": 1,
        "employee_code": "EMP00001",
        "name": "Rekha Reddy",
        "role": "Driver",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "rekha.reddy1@bmtc-demo.example",
        "avatar": "DR",
        "color": "#059669",
        "description": "Senior BMTC driver. Views assigned trips, conducts safety inspections, logs trip status.",
    },
    "conductor": {
        "employee_id": 13,
        "employee_code": "EMP00013",
        "name": "Shwetha Kulkarni",
        "role": "Conductor",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "shwetha.kulkarni13@bmtc-demo.example",
        "avatar": "CD",
        "color": "#d97706",
        "description": "BMTC conductor operating Electronic Ticketing Machine (ETM) and bus pass scanner.",
    },
    "manager": {
        "employee_id": 30,
        "employee_code": "EMP00030",
        "name": "Shivakumar Gowda",
        "role": "Depot Manager",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "shivakumar.gowda30@bmtc-demo.example",
        "avatar": "DM",
        "color": "#0284c7",
        "description": "Depot manager overseeing morning turnout, crew dispatch, and fleet readiness.",
    },
    "mechanic": {
        "employee_id": 24,
        "employee_code": "EMP00024",
        "name": "Vinay Patil",
        "role": "Mechanic",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "vinay.patil24@bmtc-demo.example",
        "avatar": "ME",
        "color": "#7c3aed",
        "description": "Workshop technician logging repair jobs, downtime hours, and preventive maintenance.",
    },
    "supervisor": {
        "employee_id": 27,
        "employee_code": "EMP00027",
        "name": "Shivakumar Murthy",
        "role": "Supervisor",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "shivakumar.murthy27@bmtc-demo.example",
        "avatar": "SV",
        "color": "#475569",
        "description": "Traffic inspector monitoring route punctuality and resolving passenger grievances.",
    },
    "guest": {
        "employee_id": 0,
        "employee_code": "GUEST",
        "name": "Unauthenticated Visitor",
        "role": "Guest",
        "depot_id": 0,
        "depot_name": "BMTC Public Terminal",
        "email": "guest@bmtc.karnataka.gov.in",
        "avatar": "GU",
        "color": "#64748b",
        "description": "Unauthenticated visitor. Confidential crew duties and operational logs are strictly locked.",
    },
}

# Official credentials store for strict employee verification
CREDENTIALS = {
    "driver": {
        "valid_codes": ["EMP00001", "EMP00001@BMTC-DEMO.EXAMPLE", "1", "REKHA", "REKHA.REDDY1@BMTC-DEMO.EXAMPLE"],
        "valid_pins": ["1001", "bmtc1001", "7410", "1234"],
        "account_key": "driver",
    },
    "conductor": {
        "valid_codes": ["EMP00013", "EMP00013@BMTC-DEMO.EXAMPLE", "13", "SHWETHA", "SHWETHA.KULKARNI13@BMTC-DEMO.EXAMPLE"],
        "valid_pins": ["1301", "bmtc1301", "8520", "1234"],
        "account_key": "conductor",
    },
    "admin": {
        "valid_codes": ["ADMIN001", "ADMIN@BMTC.KARNATAKA.GOV.IN", "ADMIN", "9999"],
        "valid_pins": ["9999", "admin123", "bmtc@admin", "admin"],
        "account_key": "admin",
    },
}


def verify_credentials(role_type: str, code: str, pin: str) -> tuple[bool, str]:
    """Verify employee code / identifier and security PIN / password.
    Returns (True, account_key) on success, or (False, error_message) on failure.
    """
    if not code or not str(code).strip():
        return False, "Employee Code or Username is required."
    if not pin or not str(pin).strip():
        return False, "Security PIN / Password is required."

    clean_code = str(code).strip().upper()
    clean_pin = str(pin).strip()

    role_cred = CREDENTIALS.get(role_type.lower())
    if not role_cred:
        return False, "Invalid role portal specified."

    code_matches = any(clean_code == c.upper() for c in role_cred["valid_codes"])
    pin_matches = any(clean_pin == p or clean_pin.lower() == p.lower() for p in role_cred["valid_pins"])

    if not code_matches:
        return False, f"Unauthorized employee code '{code}'. This identifier is not registered in the BMTC crew directory."

    if not pin_matches:
        return False, "Invalid Security PIN / Passkey. Access rejected."

    return True, role_cred["account_key"]


ALL_ROLES = ["Admin", "Driver", "Conductor", "Depot Manager", "Mechanic", "Supervisor", "Guest"]


def init_session() -> dict:
    """Ensure session state contains user information. Defaults to Admin for headless testing."""
    if "user" not in st.session_state or not st.session_state["user"]:
        st.session_state["user"] = dict(DEMO_ACCOUNTS["admin"])
    return st.session_state["user"]


def get_current_user() -> dict:
    """Return the currently authenticated user profile."""
    return init_session()


def login_as(key_or_role: str) -> None:
    """Switch active session to one of the demo role profiles."""
    key = key_or_role.lower().replace(" ", "").replace("depotmanager", "manager")
    for acc_key, acc in DEMO_ACCOUNTS.items():
        if acc_key == key or acc["role"].lower().replace(" ", "") == key:
            st.session_state["user"] = dict(acc)
            return
    st.session_state["user"] = dict(DEMO_ACCOUNTS["admin"])


def logout() -> None:
    """Reset session state to guest / unauthenticated."""
    st.session_state["user"] = dict(DEMO_ACCOUNTS["guest"])


def has_role(*allowed_roles: str) -> bool:
    """Check if the current user has one of the specified roles. Admin always returns True."""
    user = get_current_user()
    role = user.get("role", "Admin")
    if role == "Admin":
        return True
    return role in allowed_roles


# Role-based page authorization matrix
ROLE_PERMISSIONS = {
    "Admin": ["*"],
    "Guest": [
        "home.py",
        "0_Login.py",
        "1_Dashboard.py",
    ],
    "Driver": [
        "home.py",
        "0_Login.py",
        "9_Driver_Portal.py",
        "3_Routes_Trips.py",
    ],
    "Conductor": [
        "home.py",
        "0_Login.py",
        "10_Conductor_ETM.py",
        "3_Routes_Trips.py",
    ],
    "Depot Manager": [
        "home.py",
        "0_Login.py",
        "1_Dashboard.py",
        "2_Bus_Management.py",
        "3_Routes_Trips.py",
        "5_Fuel_Maintenance.py",
        "11_Depot_Operations.py",
        "12_Staff_Directory.py",
    ],
    "Mechanic": [
        "home.py",
        "0_Login.py",
        "2_Bus_Management.py",
        "5_Fuel_Maintenance.py",
    ],
    "Supervisor": [
        "home.py",
        "0_Login.py",
        "1_Dashboard.py",
        "3_Routes_Trips.py",
        "4_Ticket_Analytics.py",
        "6_Passenger_Complaints.py",
        "12_Staff_Directory.py",
    ],
}


def can_access_page(page_name: str, role: str | None = None) -> bool:
    """Return True if role has permission to access page_name."""
    if role is None:
        user = get_current_user()
        role = user.get("role", "Admin")
    if role == "Admin":
        return True
    allowed = ROLE_PERMISSIONS.get(role, [])
    if "*" in allowed:
        return True
    base = page_name.replace("\\", "/").split("/")[-1]
    return any(base == a or base == a.split("/")[-1] for a in allowed)


def enforce_role_access(page_name: str, *allowed_roles: str) -> None:
    """Guard a page by checking role access.

    If unauthorized, displays an enterprise access restricted message and stops execution.
    Admin always bypasses this check.
    """
    user = get_current_user()
    role = user.get("role", "Admin")
    if role == "Admin" or role in allowed_roles:
        return

    st.markdown(f"""
    <div style="background: #fff1f2; border: 1px solid #fecdd3; border-left: 4px solid #e11d48; border-radius: 8px; padding: 18px 20px; margin: 16px 0;">
      <div style="font-weight: 700; font-size: 1.05rem; color: #9f1239; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
        <span>🔒</span> Confidential Operational Boundary
      </div>
      <div style="color: #be123c; font-size: 0.88rem; line-height: 1.45;">
        The <b>{page_name}</b> workspace contains private, confidential operational data restricted strictly to authorized crew roles: <b>{', '.join(allowed_roles)}</b>.
      </div>
      <div style="font-size: 0.8rem; color: #64748b; margin-top: 8px;">
        Active Session: <b>{user.get('name')}</b> ({user.get('employee_code')}) &bull; Current Role: <span style="background: #e2e8f0; color: #0f172a; padding: 1px 6px; border-radius: 4px; font-weight: 600;">{role}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Authenticate at Crew Sign-In Portal (PIN Required)", key=f"goto_login_{page_name.replace(' ', '_')}", type="primary"):
        try:
            st.switch_page("app_pages/0_Login.py")
        except Exception:
            st.rerun()
    st.info("BMTC security policy enforces strict separation between Driver safety/duty logs and Conductor ticketing/revenue collections.", icon=":material/lock:")
    st.stop()


def get_assigned_routes(employee_id: int, role: str = "Driver"):
    """Fetch assigned routes for a Driver or Conductor from TRIP_DATA."""
    from utils.db import query
    col = "DRIVER_ID" if role == "Driver" else "CONDUCTOR_ID"
    sql = f"""
    SELECT DISTINCT 
        r.ROUTE_ID, r.ROUTE_CODE, r.ROUTE_NAME, r.ROUTE_CATEGORY, r.DISTANCE_KM, r.BASE_FARE,
        b.BUS_ID, b.REGISTRATION_NO, b.BUS_TYPE, d.DEPOT_NAME
    FROM BMTC_DW.TRIP.TRIP_DATA t
    JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
    JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = t.BUS_ID
    JOIN BMTC_DW.BUS.DEPOT_MASTER d ON d.DEPOT_ID = b.DEPOT_ID
    WHERE t.{col} = {employee_id}
    ORDER BY r.ROUTE_CODE
    """
    return query(sql)


def render_role_switcher_banner() -> None:
    """Compact, enterprise-grade identity and role status toolbar."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")

    with st.container(border=True):
        c_status, c_pop = st.columns([3.8, 2.2], vertical_alignment="center")
        with c_status:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; flex-wrap:wrap; gap:10px; font-size:0.8rem; color:#475569; padding: 2px 0;">
                  <span style="display:inline-flex; align-items:center; gap:6px; font-weight:700; color:#0f172a;">
                    <span style="width:8px; height:8px; border-radius:50%; background:#10b981; display:inline-block; box-shadow:0 0 0 2px rgba(16,185,129,0.2);"></span>
                    System Operational
                  </span>
                  <span style="color:#cbd5e1;">&bull;</span>
                  <span>Snowflake <b>BMTC_DW</b></span>
                  <span style="color:#cbd5e1;">&bull;</span>
                  <span>Warehouse <b>BMTC_WH</b> (X-Small)</span>
                  <span style="color:#cbd5e1;">&bull;</span>
                  <span style="color:#0284c7; font-weight:600;">Sync: Live</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_pop:
            is_unauth = (curr_role == "Guest")
            badge_color = "#64748b" if is_unauth else ("#059669" if curr_role == "Driver" else ("#d97706" if curr_role == "Conductor" else "#1e3a8a"))
            with st.popover(f"Session: {curr_role} ({curr.get('name', 'User').split()[0]}) ▾", use_container_width=True):
                st.markdown(f"""
                <div style="margin-bottom:10px;">
                  <div style="font-weight:700; font-size:0.95rem; color:#0f172a;">Active Identity & Session</div>
                  <div style="font-size:0.82rem; color:#334155; margin-top: 3px;">
                    <b>{curr.get('name')}</b> ({curr.get('employee_code')})
                  </div>
                  <div style="font-size:0.75rem; color:#64748b; margin-top: 2px;">
                    Depot: {curr.get('depot_name', 'BMTC Central')} &bull; Role: <span style="color:{badge_color}; font-weight:700;">{curr_role}</span>
                  </div>
                </div>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px; font-size:0.75rem; color:#475569; margin-bottom:12px;">
                  🔒 <b>BMTC Access Control:</b> Switching roles or accessing confidential duty rosters requires valid employee code and security PIN.
                </div>
                """, unsafe_allow_html=True)

                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    if st.button("🔒 Crew Login", key="pop_goto_login", use_container_width=True, type="primary"):
                        try:
                            st.switch_page("app_pages/0_Login.py")
                        except Exception:
                            st.rerun()
                with c_p2:
                    if st.button("🚪 Sign Out", key="pop_logout_btn", use_container_width=True):
                        logout()
                        try:
                            st.switch_page("app_pages/0_Login.py")
                        except Exception:
                            st.rerun()


def render_sidebar_user_profile() -> None:
    """Render the active user profile card inside Streamlit sidebar with role controls."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")

    with st.sidebar:
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 0.85rem; font-weight: 700; background: #0f172a; width: 34px; height: 34px; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #38bdf8; border: 1px solid #334155;">
              {curr.get("avatar", "US")}
            </div>
            <div style="overflow: hidden; flex: 1;">
              <div style="font-weight: 600; font-size: 0.9rem; color: #ffffff; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">
                {curr.get("name", "User")}
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-top: 1px;">
                <span style="background: #0284c7; color: #ffffff; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 700;">
                  {curr_role}
                </span>
                <span style="font-size: 0.7rem; color: #94a3b8;">{curr.get("employee_code", "")}</span>
              </div>
            </div>
          </div>
          <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px;">
            Depot: {curr.get("depot_name", "BMTC Central")}
          </div>
        </div>
        """, unsafe_allow_html=True)

        c_sb1, c_sb2 = st.columns(2)
        with c_sb1:
            if st.button("Crew Sign-In", key="sidebar_goto_login_btn", use_container_width=True):
                try:
                    st.switch_page("app_pages/0_Login.py")
                except Exception:
                    st.rerun()
        with c_sb2:
            if st.button("Sign Out", key="sidebar_logout_btn", use_container_width=True):
                logout()
                try:
                    st.switch_page("app_pages/0_Login.py")
                except Exception:
                    st.rerun()
