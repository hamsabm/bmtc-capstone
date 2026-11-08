"""Home page: connection status, how the system fits together, table inventory."""
import streamlit as st

from utils.db import connection_ok, query
from utils.ui import num, page, show_table

page("BMTC Data Warehouse & Analytics System",
     "Operations, fleet, revenue and passenger analytics on Snowflake - synthetic academic dataset")

ok, info = connection_ok()   # page() already stopped the script if the connection failed
st.success(f"Connected to Snowflake - {info}", icon=":material/check_circle:")

st.warning("All data in this application is **synthetic academic data** generated for a capstone project. "
           "It is not official BMTC operational data; people, phone numbers and registrations are fictitious.",
           icon=":material/info:")

st.subheader("How the system fits together")
st.markdown("""
`User -> Streamlit page -> Python logic (utils/) -> Snowflake connector -> BMTC_DW (BUS / TRIP / PASSENGER) -> result -> User`

| Page | What you can do |
|---|---|
| **Dashboard** | Live KPIs and headline charts |
| **Bus Management** | Search/filter the fleet, depot & type analysis, change a bus status (transaction + audit) |
| **Routes & Trips** | Route search, route detail, trip log, top/bottom routes |
| **Ticket Analytics** | Ticket volume, revenue, payment mix, route-wise and time trends |
| **Fuel & Maintenance** | Fuel efficiency (Python UDF), maintenance history, log a workshop job |
| **Passenger & Complaints** | Passes (secure view), complaint JSON analytics, triage queue, register a complaint |
| **Advanced Analytics** | Run the catalogue of advanced SQL (CTE, windows, subqueries) |
| **Data Management** | Time Travel, clone, stream/task, Snowpipe, security and warehouse status (read-only) |
""")

st.subheader("Tables in BMTC_DW")
tables = query("""
SELECT TABLE_SCHEMA AS SCHEMA_NAME, TABLE_NAME, ROW_COUNT, ROUND(BYTES / 1024, 1) AS SIZE_KB,
       IFF(IS_TRANSIENT = 'YES', 'TRANSIENT', 'PERMANENT') AS TABLE_KIND, COMMENT
FROM BMTC_DW.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('BUS', 'TRIP', 'PASSENGER') AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME""")
if not tables.empty:
    st.metric("Rows across project tables", num(tables["ROW_COUNT"].sum()))
show_table(tables)
