r"""BMTC Data Warehouse & Analytics System - Streamlit entry point (role-based navigation).

Run:  .\venv\Scripts\python.exe -m streamlit run app.py
"""
import streamlit as st

from utils.auth import get_current_user

st.set_page_config(page_title="BMTC Analytics", page_icon=":material/directions_bus:", layout="wide")

user = get_current_user()
role = user.get("role", "Admin")

# Core pages
home_page = st.Page("home.py", title="Home", icon=":material/home:", default=(role == "Admin"))
dashboard_page = st.Page("app_pages/1_Dashboard.py", url_path="dashboard", title="Dashboard", icon=":material/dashboard:")

# Role-specific operational portals
driver_page = st.Page("app_pages/9_Driver_Portal.py", url_path="driver-portal", title="Driver Portal", icon=":material/badge:", default=(role == "Driver"))
conductor_page = st.Page("app_pages/10_Conductor_ETM.py", url_path="conductor-etm", title="Conductor ETM", icon=":material/confirmation_number:", default=(role == "Conductor"))
depot_page = st.Page("app_pages/11_Depot_Operations.py", url_path="depot-operations", title="Depot Command", icon=":material/domain:", default=(role == "Depot Manager"))
staff_page = st.Page("app_pages/12_Staff_Directory.py", url_path="staff-directory", title="Staff Directory", icon=":material/badge:")

# General Operations & Analytics
bus_page = st.Page("app_pages/2_Bus_Management.py", url_path="bus-management", title="Bus Management", icon=":material/directions_bus:")
routes_page = st.Page("app_pages/3_Routes_Trips.py", url_path="routes-trips", title="Routes & Trips", icon=":material/route:")
ticket_page = st.Page("app_pages/4_Ticket_Analytics.py", url_path="ticket-analytics", title="Ticket Analytics", icon=":material/analytics:")
fuel_page = st.Page("app_pages/5_Fuel_Maintenance.py", url_path="fuel-maintenance", title="Fuel & Maintenance", icon=":material/build:", default=(role == "Mechanic"))
passengers_page = st.Page("app_pages/6_Passenger_Complaints.py", url_path="passengers-complaints", title="Passengers & Complaints", icon=":material/groups:", default=(role == "Supervisor"))
advanced_page = st.Page("app_pages/7_Advanced_Analytics.py", url_path="advanced-analytics", title="Advanced Analytics", icon=":material/query_stats:")
data_page = st.Page("app_pages/8_Data_Management.py", url_path="data-management", title="Data Management", icon=":material/database:")

# Role-specific dynamic navigation
if role == "Driver":
    nav_dict = {
        "My Duty": [driver_page],
        "Transit Network": [routes_page],
        "Overview": [home_page],
    }
elif role == "Conductor":
    nav_dict = {
        "ETM & Passes": [conductor_page],
        "Transit Network": [routes_page],
        "Overview": [home_page],
    }
elif role == "Mechanic":
    nav_dict = {
        "Workshop": [fuel_page],
        "Fleet Register": [bus_page],
        "Overview": [home_page],
    }
elif role == "Depot Manager":
    nav_dict = {
        "Depot Command": [depot_page, dashboard_page],
        "Fleet & Crew": [bus_page, staff_page, fuel_page],
        "Operations": [routes_page],
        "Overview": [home_page],
    }
elif role == "Supervisor":
    nav_dict = {
        "Supervision & Grievances": [passengers_page],
        "Operations": [routes_page, ticket_page, dashboard_page],
        "Staff Directory": [staff_page],
        "Overview": [home_page],
    }
else:  # Admin / Default (has access to all modules and tools)
    nav_dict = {
        "Overview": [home_page, dashboard_page],
        "Role Portals": [driver_page, conductor_page, depot_page, staff_page],
        "Operations": [bus_page, routes_page, ticket_page, fuel_page],
        "Passengers": [passengers_page],
        "Analytics & Platform": [advanced_page, data_page],
    }

nav = st.navigation(nav_dict)
nav.run()
