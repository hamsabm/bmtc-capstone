import streamlit as st

from utils.db import query
from utils.ui import chart, page, show_table

page("Data Management", "Read-only view of Snowflake platform features. Destructive operations stay in "
                        "reviewed SQL scripts (sql/07, sql/08) - nothing on this page modifies project data, "
                        "except running the fleet-health procedure, which only appends a snapshot row.")

tabs = st.tabs(["Time Travel", "Zero-copy clone", "Stream & Task", "Snowpipe", "Python procedure",
                "Security", "Warehouse & storage"])

with tabs[0]:
    st.markdown("Compare current route fares with the table as it was *N* minutes ago "
                "(`AT (OFFSET => ...)`). The fare-error recovery demo is in `sql/07_time_travel_clone.sql`; "
                "its pre-error snapshot is kept in `TRIP.ROUTE_MASTER_PRE_FARE_ERROR`.")
    minutes = st.slider("Minutes back", 1, 600, 5)
    tt = query(f"""SELECT cur.ROUTE_CODE, cur.ROUTE_CATEGORY, old.BASE_FARE AS FARE_THEN, cur.BASE_FARE AS FARE_NOW,
                          IFF(old.BASE_FARE = cur.BASE_FARE, 'unchanged', 'CHANGED') AS DIFF
                   FROM BMTC_DW.TRIP.ROUTE_MASTER cur
                   JOIN BMTC_DW.TRIP.ROUTE_MASTER AT (OFFSET => -60 * {int(minutes)}) old ON old.ROUTE_ID = cur.ROUTE_ID
                   ORDER BY DIFF, cur.ROUTE_ID""", cache=False)
    if tt.empty:
        st.caption("If the offset predates the table's creation or exceeds the retention period, "
                   "Snowflake returns an error instead of history.")
    show_table(tt, height=300)
    st.markdown("**Audit snapshot created by the Time Travel clone (correct fares before the error)**")
    show_table(query("""SELECT s.ROUTE_CODE, s.BASE_FARE AS SNAPSHOT_FARE, r.BASE_FARE AS CURRENT_FARE
                        FROM BMTC_DW.TRIP.ROUTE_MASTER_PRE_FARE_ERROR s
                        JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = s.ROUTE_ID
                        WHERE s.ROUTE_CATEGORY = 'AC Vajra' ORDER BY s.ROUTE_ID"""))

with tabs[1]:
    st.markdown("`BUS.BUS_MASTER_CLONE` is a zero-copy clone used to test a fleet-renewal rule "
                "(retire diesel buses built before 2018) without touching production.")
    cmp = query("""SELECT 'Production' AS COPY, STATUS, COUNT(*) AS BUSES FROM BMTC_DW.BUS.BUS_MASTER GROUP BY STATUS
                   UNION ALL
                   SELECT 'Clone (renewal test)', STATUS, COUNT(*) FROM BMTC_DW.BUS.BUS_MASTER_CLONE GROUP BY STATUS""")
    chart(cmp, "bar", "COPY", "BUSES", "Bus status: production vs clone", color="STATUS")
    show_table(query("""SELECT d.DEPOT_NAME, COUNT(*) AS BUSES_TO_REPLACE, SUM(c.SEATING_CAPACITY) AS SEATS_TO_REPLACE
                        FROM BMTC_DW.BUS.BUS_MASTER_CLONE c JOIN BMTC_DW.BUS.DEPOT_MASTER d ON d.DEPOT_ID = c.DEPOT_ID
                        WHERE c.STATUS = 'RETIRED' GROUP BY d.DEPOT_NAME ORDER BY SEATS_TO_REPLACE DESC"""))

with tabs[2]:
    st.markdown("`TRIP.TRIP_DATA` -> **`TRIP.TRIP_DATA_STREAM`** -> **`TRIP.TASK_REFRESH_TRIP_SUMMARY`** "
                "(calls `TRIP.SP_APPLY_TRIP_CHANGES`) -> `TRIP.TRIP_ANALYTICS_SUMMARY`")
    s = query("SELECT SYSTEM$STREAM_HAS_DATA('BMTC_DW.TRIP.TRIP_DATA_STREAM') AS PENDING, "
              "(SELECT MISMATCHED_ROUTE_DAYS FROM BMTC_DW.TRIP.V_SUMMARY_RECONCILIATION) AS MISMATCHES", cache=False)
    if not s.empty:
        c = st.columns(2)
        c[0].metric("Stream has unprocessed changes", "Yes" if s.iloc[0]["PENDING"] else "No")
        c[1].metric("Summary vs source mismatches", int(s.iloc[0]["MISMATCHES"]))
    st.markdown("**Task definition**")
    tasks = query("SHOW TASKS IN SCHEMA BMTC_DW.TRIP", cache=False)
    if not tasks.empty:
        show_table(tasks[[c for c in ["name", "state", "schedule", "warehouse", "condition", "definition"] if c in tasks]])
    st.markdown("**Task run history**")
    show_table(query("""SELECT NAME, STATE, SCHEDULED_TIME, COMPLETED_TIME, ERROR_MESSAGE
                        FROM TABLE(BMTC_DW.INFORMATION_SCHEMA.TASK_HISTORY(
                             TASK_NAME => 'TASK_REFRESH_TRIP_SUMMARY', RESULT_LIMIT => 20))
                        ORDER BY SCHEDULED_TIME DESC""", cache=False), "No task runs recorded in the last 7 days.")
    st.markdown("**Changes applied by the task**")
    show_table(query("SELECT * FROM BMTC_DW.TRIP.TASK_RUN_LOG ORDER BY RUN_AT DESC", cache=False))
    summ = query("""SELECT TRIP_DATE, SUM(TRIPS) AS TRIPS, SUM(PASSENGERS) AS PASSENGERS
                    FROM BMTC_DW.TRIP.TRIP_ANALYTICS_SUMMARY GROUP BY 1 ORDER BY 1""")
    chart(summ, "line", "TRIP_DATE", "PASSENGERS", "Daily passengers from the task-maintained summary table")

with tabs[3]:
    st.markdown("`STAGING.PIPE_COMPLAINTS_FEED` loads new complaint JSON files from "
                "`@STAGING.BMTC_INTERNAL_STAGE/feed/` into `PASSENGER.COMPLAINTS_JSON`.")
    ps = query("SELECT SYSTEM$PIPE_STATUS('BMTC_DW.STAGING.PIPE_COMPLAINTS_FEED') AS STATUS", cache=False)
    if not ps.empty:
        st.json(ps.iloc[0]["STATUS"])
    show_table(query("""SELECT INGESTION, COUNT(*) AS COMPLAINTS FROM BMTC_DW.PASSENGER.V_COMPLAINT_ANALYTICS
                        GROUP BY 1 ORDER BY 2 DESC""", cache=False))

with tabs[4]:
    st.markdown("`TRIP.SP_FLEET_HEALTH_SNAPSHOT()` - a Python (Snowpark) stored procedure that scores each "
                "depot from UDF fuel classes and serious maintenance jobs, and appends a snapshot.")
    if st.button("Run fleet health snapshot now"):
        res = query("CALL BMTC_DW.TRIP.SP_FLEET_HEALTH_SNAPSHOT()", cache=False)
        if not res.empty:
            st.success(res.iloc[0, 0])
    snap = query("""SELECT DEPOT_NAME, BUSES, POOR_EFFICIENCY_FILLS, SERIOUS_MAINTENANCE_JOBS, MAINTENANCE_COST,
                           HEALTH_SCORE, SNAPSHOT_AT
                    FROM BMTC_DW.TRIP.FLEET_HEALTH_SNAPSHOT
                    QUALIFY SNAPSHOT_AT = MAX(SNAPSHOT_AT) OVER () ORDER BY HEALTH_SCORE""", cache=False)
    chart(snap, "bar", "DEPOT_NAME", "HEALTH_SCORE", "Depot fleet health score (latest snapshot)", horizontal=True)
    show_table(snap)

with tabs[5]:
    st.markdown("Role hierarchy: `BMTC_VIEWER -> BMTC_ANALYST -> BMTC_MANAGER -> BMTC_ADMIN -> SYSADMIN`")
    roles = query("SHOW ROLES LIKE 'BMTC%'", cache=False)
    if not roles.empty:
        show_table(roles[[c for c in ["name", "comment", "granted_roles", "granted_to_roles", "assigned_to_users"] if c in roles]])
    st.markdown("**Masking and row access policies attached**")
    show_table(query("""SELECT REF_ENTITY_NAME AS OBJECT, REF_COLUMN_NAME AS COLUMN_NAME, POLICY_NAME, POLICY_KIND
                        FROM TABLE(BMTC_DW.INFORMATION_SCHEMA.POLICY_REFERENCES(
                             REF_ENTITY_NAME => 'BMTC_DW.PASSENGER.PASS_DATA', REF_ENTITY_DOMAIN => 'table'))
                        UNION ALL
                        SELECT REF_ENTITY_NAME, REF_COLUMN_NAME, POLICY_NAME, POLICY_KIND
                        FROM TABLE(BMTC_DW.INFORMATION_SCHEMA.POLICY_REFERENCES(
                             REF_ENTITY_NAME => 'BMTC_DW.BUS.EMPLOYEE_MASTER', REF_ENTITY_DOMAIN => 'table'))"""),
               "Policy metadata is visible only to administrators. This application runs with a least-privilege "
               "role, and PII is masked for it (see sql/09_security.sql).")
    st.markdown("**Secure views**")
    sv = query("SHOW VIEWS IN DATABASE BMTC_DW", cache=False)
    if not sv.empty and "is_secure" in sv:
        show_table(sv[sv["is_secure"].astype(str).str.lower() == "true"][["schema_name", "name", "comment"]])

with tabs[6]:
    wh = query("SHOW WAREHOUSES LIKE 'BMTC_WH'", cache=False)
    if not wh.empty:
        show_table(wh[[c for c in ["name", "state", "size", "auto_suspend", "auto_resume", "resource_monitor",
                                   "min_cluster_count", "max_cluster_count"] if c in wh]])
    st.markdown("**Table types and storage**")
    show_table(query("""SELECT TABLE_SCHEMA, TABLE_NAME, IFF(IS_TRANSIENT = 'YES', 'TRANSIENT', 'PERMANENT') AS KIND,
                               ROW_COUNT, ROUND(BYTES / 1024, 1) AS KB, RETENTION_TIME AS TIME_TRAVEL_DAYS
                        FROM BMTC_DW.INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'
                        ORDER BY TABLE_SCHEMA, TABLE_NAME"""))
