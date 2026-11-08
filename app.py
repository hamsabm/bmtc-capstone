r"""BMTC Data Warehouse & Analytics System - Streamlit entry point (navigation).

Run:  .\venv\Scripts\python.exe -m streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="BMTC Analytics", page_icon=":material/directions_bus:", layout="wide")

nav = st.navigation({
    "Overview": [
        st.Page("home.py", title="Home", icon=":material/home:", default=True),
        st.Page("app_pages/1_Dashboard.py", url_path="dashboard", title="Dashboard", icon=":material/dashboard:"),
    ],
    "Operations": [
        st.Page("app_pages/2_Bus_Management.py", url_path="bus-management", title="Bus Management", icon=":material/directions_bus:"),
        st.Page("app_pages/3_Routes_Trips.py", url_path="routes-trips", title="Routes & Trips", icon=":material/route:"),
        st.Page("app_pages/4_Ticket_Analytics.py", url_path="ticket-analytics", title="Ticket Analytics", icon=":material/confirmation_number:"),
        st.Page("app_pages/5_Fuel_Maintenance.py", url_path="fuel-maintenance", title="Fuel & Maintenance", icon=":material/build:"),
    ],
    "Passengers": [
        st.Page("app_pages/6_Passenger_Complaints.py", url_path="passengers-complaints", title="Passengers & Complaints", icon=":material/groups:"),
    ],
    "Analytics & Platform": [
        st.Page("app_pages/7_Advanced_Analytics.py", url_path="advanced-analytics", title="Advanced Analytics", icon=":material/query_stats:"),
        st.Page("app_pages/8_Data_Management.py", url_path="data-management", title="Data Management", icon=":material/database:"),
    ],
})
nav.run()
