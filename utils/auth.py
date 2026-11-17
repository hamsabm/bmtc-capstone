"""Role-Based Access Control (RBAC) and Authentication for BMTC Capstone.

Supported Roles:
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
        "color": "#1e3a8a",
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
        "color": "#eb6834",
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
        "color": "#1baf7a",
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
        "color": "#eda100",
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
        "color": "#e87ba4",
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
        "color": "#6250d6",
        "description": "Traffic inspector monitoring route punctuality and resolving passenger grievances.",
    },
}

ALL_ROLES = ["Admin", "Depot Manager", "Driver", "Conductor", "Mechanic", "Supervisor"]


def init_session() -> dict:
    """Ensure session state contains user information. Defaults to Admin for headless testing."""
    if "user" not in st.session_state or not st.session_state["user"]:
        # Default user is Admin to preserve seamless test suite execution
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
    # Fallback to Admin
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
    """Compact role switcher pill bar displayed on Home or Portals for instant demonstration."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")

    st.markdown("""
    <style>
    .role-bar-container {
        background: #ffffff;
        border: 1px solid #dbe5f4;
        border-radius: 14px;
        padding: 10px 16px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 12px rgba(30,58,138,0.05);
    }
    .role-badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns([2.5, 4.5])
        with c1:
            st.markdown(
                f'<div style="font-size: 0.82rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">'
                f'Active Role & Identity</div>'
                f'<div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">'
                f'<span style="font-size: 1.4rem;">{curr.get("avatar", "👤")}</span>'
                f'<div><strong style="color: #0f172a; font-size: 1.05rem;">{curr.get("name", "User")}</strong>'
                f'<span style="background: {curr.get("color", "#1e3a8a")}; color: #fff; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin-left: 6px;">'
                f'{curr_role}</span>'
                f'<div style="font-size: 0.78rem; color: #64748b;">{curr.get("depot_name", "All Depots")} · {curr.get("employee_code", "")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown('<div style="font-size: 0.82rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">'
                        'Switch Role Demo</div>', unsafe_allow_html=True)
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
                if col.button(f"{icon} {lbl}", key=f"role_btn_{key}", disabled=is_curr, use_container_width=True):
                    login_as(key)
                    st.rerun()


def render_sidebar_user_profile() -> None:
    """Render the active user profile card inside Streamlit sidebar with role switcher."""
    curr = get_current_user()
    curr_role = curr.get("role", "Admin")

    with st.sidebar:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18); border-radius: 12px; padding: 12px; margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="font-size: 1.6rem; background: rgba(255,255,255,0.14); width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
              {curr.get("avatar", "👤")}
            </div>
            <div style="overflow: hidden;">
              <div style="font-weight: 700; font-size: 0.92rem; color: #ffffff; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">
                {curr.get("name", "User")}
              </div>
              <div style="font-size: 0.74rem; color: #a5c4ff;">
                {curr_role} · {curr.get("employee_code", "")}
              </div>
            </div>
          </div>
          <div style="font-size: 0.72rem; color: #d0e1fd; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 5px;">
            📍 {curr.get("depot_name", "BMTC Central")}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick role switcher in sidebar
        role_keys = {
            "👑 Admin (Full DW)": "admin",
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
            "Switch Role (Demo)",
            labels,
            index=current_idx,
            key="sidebar_role_selector",
            help="Switch roles to view tailored permissions, pages, and operational tools",
        )

        selected_key = role_keys[selected_role_label]
        if DEMO_ACCOUNTS[selected_key]["role"] != curr_role:
            login_as(selected_key)
            st.rerun()
