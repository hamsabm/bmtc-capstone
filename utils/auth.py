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
        "avatar": "👑",
        "color": "#1e40af",
        "description": "Full system administrator with database, time travel, clone, security & analytics access.",
    },
    "manager": {
        "employee_id": 30,
        "employee_code": "EMP00030",
        "name": "Shivakumar Gowda",
        "role": "Depot Manager",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "shivakumar.gowda30@bmtc-demo.example",
        "avatar": "🏢",
        "color": "#ea580c",
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
        "avatar": "🚌",
        "color": "#059669",
        "description": "Senior BMTC driver. Views assigned trips, conducts safety inspections, logs trips.",
    },
    "conductor": {
        "employee_id": 13,
        "employee_code": "EMP00013",
        "name": "Shwetha Kulkarni",
        "role": "Conductor",
        "depot_id": 1,
        "depot_name": "Shanthinagar Depot-01",
        "email": "shwetha.kulkarni13@bmtc-demo.example",
        "avatar": "🎟️",
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
        "avatar": "🔧",
        "color": "#db2777",
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
        "avatar": "📋",
        "color": "#7c3aed",
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
    key = key_or_role.lower()
    for acc_key, acc in DEMO_ACCOUNTS.items():
        if acc_key == key or acc["role"].lower() == key:
            st.session_state["user"] = dict(acc)
            return
    st.session_state["user"] = dict(DEMO_ACCOUNTS["admin"])


def logout() -> None:
    """Reset session state to admin (or public preview)."""
    st.session_state["user"] = dict(DEMO_ACCOUNTS["admin"])


def has_role(*allowed_roles: str) -> bool:
    """Check if the current user has one of the specified roles. Admin always returns True."""
    user = get_current_user()
    role = user.get("role", "Admin")
    if role == "Admin":
        return True
    return role in allowed_roles


def render_role_switcher_banner() -> None:
    """Enterprise role switcher card displayed on Home and Portals."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")
    role_color = curr.get("color", "#1e40af")

    with st.container(border=True):
        c1, c2 = st.columns([2.6, 4.4])
        with c1:
            st.markdown(
                f"""
                <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">
                  Active Identity & Session
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                  <div style="font-size: 1.85rem; width: 48px; height: 48px; border-radius: 12px; background: {role_color}18; border: 2px solid {role_color}40; display: flex; align-items: center; justify-content: center;">
                    {curr.get("avatar", "👤")}
                  </div>
                  <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span style="color: #0f172a; font-size: 1.12rem; font-weight: 800;">{curr.get("name", "User")}</span>
                      <span style="background: {role_color}; color: #ffffff; padding: 2px 9px; border-radius: 6px; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.04em;">
                        {curr_role.upper()}
                      </span>
                    </div>
                    <div style="font-size: 0.78rem; color: #64748b; margin-top: 2px;">
                      🏢 {curr.get("depot_name", "All Depots")} &bull; 🆔 <code>{curr.get("employee_code", "")}</code>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                """
                <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">
                  Instant Role Simulation (1-Click Switcher)
                </div>
                """,
                unsafe_allow_html=True,
            )
            cols = st.columns(6)
            roles = [
                ("Admin", "admin", "👑"),
                ("Depot Mgr", "manager", "🏢"),
                ("Driver", "driver", "🚌"),
                ("Conductor", "conductor", "🎟️"),
                ("Mechanic", "mechanic", "🔧"),
                ("Supervisor", "supervisor", "📋"),
            ]
            for col, (lbl, key, icon) in zip(cols, roles):
                is_curr = (DEMO_ACCOUNTS[key]["role"] == curr_role)
                btn_label = f"✓ {lbl}" if is_curr else f"{icon} {lbl}"
                if col.button(btn_label, key=f"role_btn_{key}", disabled=is_curr, use_container_width=True,
                              help=DEMO_ACCOUNTS[key]["description"]):
                    login_as(key)
                    st.rerun()


def render_sidebar_user_profile() -> None:
    """Render the active user profile card inside Streamlit sidebar with role switcher."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")
    role_color = curr.get("color", "#38bdf8")

    with st.sidebar:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); border-left: 4px solid {role_color}; border-radius: 12px; padding: 12px 14px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 1.5rem; background: rgba(255,255,255,0.1); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.18);">
              {curr.get("avatar", "👤")}
            </div>
            <div style="overflow: hidden; flex: 1;">
              <div style="font-weight: 700; font-size: 0.94rem; color: #ffffff; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">
                {curr.get("name", "User")}
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-top: 1px;">
                <span style="background: {role_color}; color: #ffffff; padding: 1px 7px; border-radius: 4px; font-size: 0.68rem; font-weight: 800;">
                  {curr_role}
                </span>
                <span style="font-size: 0.72rem; color: #94a3b8;">{curr.get("employee_code", "")}</span>
              </div>
            </div>
          </div>
          <div style="font-size: 0.72rem; color: #cbd5e1; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px;">
            📍 {curr.get("depot_name", "BMTC Central")}
          </div>
        </div>
        """, unsafe_allow_html=True)

        role_keys = {
            "👑 Admin (Full System)": "admin",
            "🏢 Depot Manager": "manager",
            "🚌 Driver": "driver",
            "🎟️ Conductor": "conductor",
            "🔧 Mechanic": "mechanic",
            "📋 Supervisor": "supervisor",
        }
        labels = list(role_keys.keys())
        current_idx = 0
        for i, l in enumerate(labels):
            if DEMO_ACCOUNTS[role_keys[l]]["role"] == curr_role:
                current_idx = i
                break

        selected_role_label = st.selectbox(
            "Active Role Identity",
            labels,
            index=current_idx,
            key="sidebar_role_selector",
            help="Switch role simulation to test permissions and tailored workflows",
        )

        selected_key = role_keys[selected_role_label]
        if DEMO_ACCOUNTS[selected_key]["role"] != curr_role:
            login_as(selected_key)
            st.rerun()
