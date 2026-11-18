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
}

ALL_ROLES = ["Admin", "Depot Manager", "Driver", "Conductor", "Mechanic", "Supervisor"]


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
    """Reset session state to admin."""
    st.session_state["user"] = dict(DEMO_ACCOUNTS["admin"])


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
    "Depot Manager": [
        "home.py",
        "1_Dashboard.py",
        "2_Bus_Management.py",
        "3_Routes_Trips.py",
        "5_Fuel_Maintenance.py",
        "11_Depot_Operations.py",
        "12_Staff_Directory.py",
    ],
    "Driver": [
        "home.py",
        "9_Driver_Portal.py",
        "3_Routes_Trips.py",
    ],
    "Conductor": [
        "home.py",
        "10_Conductor_ETM.py",
        "3_Routes_Trips.py",
    ],
    "Mechanic": [
        "home.py",
        "2_Bus_Management.py",
        "5_Fuel_Maintenance.py",
    ],
    "Supervisor": [
        "home.py",
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
      <div style="font-weight: 700; font-size: 1.05rem; color: #9f1239; margin-bottom: 4px;">
        Restricted Operational Access
      </div>
      <div style="color: #be123c; font-size: 0.88rem; line-height: 1.45;">
        The <b>{page_name}</b> workspace is restricted to authorized roles: <b>{', '.join(allowed_roles)}</b>.
      </div>
      <div style="font-size: 0.8rem; color: #64748b; margin-top: 8px;">
        Active Session: <b>{user.get('name')}</b> ({user.get('employee_code')}) &bull; Current Role: <span style="background: #e2e8f0; color: #0f172a; padding: 1px 6px; border-radius: 4px; font-weight: 600;">{role}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.5, 3])
    if allowed_roles:
        target_role = allowed_roles[0].lower().replace(" ", "").replace("depotmanager", "manager")
        if target_role in DEMO_ACCOUNTS:
            if c1.button(f"Switch to {allowed_roles[0]} Role", key=f"switch_to_{target_role}", use_container_width=True):
                login_as(target_role)
                st.rerun()
    st.info("Use the role switcher at the top or in the sidebar to simulate another identity.", icon=":material/badge:")
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
    """Compact, enterprise-grade identity and role switcher control."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")

    with st.container(border=True):
        c_id, c_switch = st.columns([3.4, 2.6])
        with c_id:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:12px; padding: 2px 0;">
                  <div style="width: 36px; height: 36px; border-radius: 6px; background: #0f172a; color: #ffffff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.9rem; border: 1px solid #334155;">
                    {curr.get("avatar", "US")}
                  </div>
                  <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span style="font-weight: 700; font-size: 0.95rem; color: #0f172a;">{curr.get("name", "User")}</span>
                      <span style="background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 1px 7px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;">
                        {curr_role.upper()}
                      </span>
                    </div>
                    <div style="font-size: 0.78rem; color: #64748b; margin-top: 1px;">
                      <span>{curr.get("depot_name", "All Depots")}</span> &bull; <code>{curr.get("employee_code", "")}</code>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_switch:
            with st.popover(f"Viewing as: {curr_role} ▾", use_container_width=True):
                st.caption("Select an operational role profile to simulate permissions & views:")
                for key, acc in DEMO_ACCOUNTS.items():
                    is_active = (acc["role"] == curr_role)
                    prefix = "✓ " if is_active else ""
                    if st.button(
                        f"{prefix}{acc['role']} &bull; {acc['name']}",
                        key=f"pop_role_{key}",
                        disabled=is_active,
                        help=acc["description"],
                        use_container_width=True,
                    ):
                        login_as(key)
                        st.rerun()


def render_sidebar_user_profile() -> None:
    """Render the active user profile card inside Streamlit sidebar with role selector."""
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

        role_keys = {
            "Admin (Full System)": "admin",
            "Depot Manager": "manager",
            "Driver": "driver",
            "Conductor": "conductor",
            "Mechanic": "mechanic",
            "Supervisor": "supervisor",
        }
        labels = list(role_keys.keys())
        current_idx = 0
        for i, l in enumerate(labels):
            if DEMO_ACCOUNTS[role_keys[l]]["role"] == curr_role:
                current_idx = i
                break

        selected_role_label = st.selectbox(
            "Simulate Role",
            labels,
            index=current_idx,
            key="sidebar_role_selector",
            help="Switch role simulation to test permissions and tailored workflows",
        )

        selected_key = role_keys[selected_role_label]
        if DEMO_ACCOUNTS[selected_key]["role"] != curr_role:
            login_as(selected_key)
            st.rerun()
