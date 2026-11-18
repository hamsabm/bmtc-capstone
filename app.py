r"""BMTC Data Warehouse & Analytics System - Streamlit entry point (role-based navigation).

Run:  .\venv\Scripts\python.exe -m streamlit run app.py
"""
import streamlit as st

from utils.auth import get_current_user

st.set_page_config(page_title="BMTC Intelligence Platform", page_icon=":material/directions_bus:", layout="wide")

user = get_current_user()
role = user.get("role", "Admin")

# Core pages
home_page = st.Page("home.py", title="Platform Overview", icon=":material/space_dashboard:", default=(role == "Admin"))
dashboard_page = st.Page("app_pages/1_Dashboard.py", url_path="dashboard", title="Executive Dashboard", icon=":material/monitoring:")

# Operational Portals
driver_page = st.Page("app_pages/9_Driver_Portal.py", url_path="driver-portal", title="Driver Portal", icon=":material/badge:", default=(role == "Driver"))
conductor_page = st.Page("app_pages/10_Conductor_ETM.py", url_path="conductor-etm", title="Conductor ETM", icon=":material/confirmation_number:", default=(role == "Conductor"))
depot_page = st.Page("app_pages/11_Depot_Operations.py", url_path="depot-operations", title="Depot Command", icon=":material/domain:", default=(role == "Depot Manager"))
staff_page = st.Page("app_pages/12_Staff_Directory.py", url_path="staff-directory", title="Staff Directory", icon=":material/contacts:")

# Transit & Fleet Operations
bus_page = st.Page("app_pages/2_Bus_Management.py", url_path="bus-management", title="Fleet Management", icon=":material/directions_bus:")
routes_page = st.Page("app_pages/3_Routes_Trips.py", url_path="routes-trips", title="Routes & Trips", icon=":material/route:")
ticket_page = st.Page("app_pages/4_Ticket_Analytics.py", url_path="ticket-analytics", title="Ticket Analytics", icon=":material/receipt_long:")
fuel_page = st.Page("app_pages/5_Fuel_Maintenance.py", url_path="fuel-maintenance", title="Fuel & Maintenance", icon=":material/build:", default=(role == "Mechanic"))
passengers_page = st.Page("app_pages/6_Passenger_Complaints.py", url_path="passengers-complaints", title="Passenger Grievances", icon=":material/groups:", default=(role == "Supervisor"))

# Platform & Data Governance
advanced_page = st.Page("app_pages/7_Advanced_Analytics.py", url_path="advanced-analytics", title="Advanced Analytics", icon=":material/query_stats:")
data_page = st.Page("app_pages/8_Data_Management.py", url_path="data-management", title="Data Platform Console", icon=":material/database:")

# Role-specific enterprise navigation
if role == "Driver":
    nav_dict = {
        "My Duty": [driver_page],
        "Transit Operations": [routes_page],
        "System Overview": [home_page],
    }
elif role == "Conductor":
    nav_dict = {
        "ETM & Ticketing": [conductor_page],
        "Transit Operations": [routes_page],
        "System Overview": [home_page],
    }
elif role == "Mechanic":
    nav_dict = {
        "Workshop Operations": [fuel_page],
        "Fleet Register": [bus_page],
        "System Overview": [home_page],
    }
elif role == "Depot Manager":
    nav_dict = {
        "Depot Command": [depot_page, dashboard_page],
        "Fleet & Crew": [bus_page, staff_page, fuel_page],
        "Transit Operations": [routes_page],
        "System Overview": [home_page],
    }
elif role == "Supervisor":
    nav_dict = {
        "Quality & Grievances": [passengers_page],
        "Operations Oversight": [routes_page, ticket_page, dashboard_page],
        "Staff Directory": [staff_page],
        "System Overview": [home_page],
    }
else:  # Admin / Default (full DW governance and analytics)
    nav_dict = {
        "Overview": [dashboard_page, home_page],
        "Operations": [bus_page, routes_page, ticket_page, fuel_page],
        "People & Crew": [driver_page, conductor_page, staff_page],
        "Depot & Field": [depot_page],
        "Passenger Intelligence": [passengers_page],
        "Platform Governance": [advanced_page, data_page],
    }

nav = st.navigation(nav_dict)
nav.run()
