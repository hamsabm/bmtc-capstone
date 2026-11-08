r"""BMTC Data Warehouse & Analytics System - Streamlit entry point (navigation).

Run:  .\venv\Scripts\python.exe -m streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="BMTC Analytics", page_icon=":material/directions_bus:", layout="wide")

nav = st.navigation({
    "Overview": [
        st.Page("home.py", title="Home", icon=":material/home:", default=True),
        st.Page("pages/1_Dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    ],
    "Operations": [
        st.Page("pages/2_Bus_Management.py", title="Bus Management", icon=":material/directions_bus:"),
        st.Page("pages/3_Routes_Trips.py", title="Routes & Trips", icon=":material/route:"),
        st.Page("pages/4_Ticket_Analytics.py", title="Ticket Analytics", icon=":material/confirmation_number:"),
        st.Page("pages/5_Fuel_Maintenance.py", title="Fuel & Maintenance", icon=":material/build:"),
    ],
    "Passengers": [
        st.Page("pages/6_Passenger_Complaints.py", title="Passengers & Complaints", icon=":material/groups:"),
    ],
    "Analytics & Platform": [
        st.Page("pages/7_Advanced_Analytics.py", title="Advanced Analytics", icon=":material/query_stats:"),
        st.Page("pages/8_Data_Management.py", title="Data Management", icon=":material/database:"),
    ],
})
nav.run()
