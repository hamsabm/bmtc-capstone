import datetime as dt

import streamlit as st

from utils import queries as Q
from utils.db import query
from utils.ui import chart, money, num, page, show_table

page("Routes & Trips", "Route network, route performance (TRIP.V_ROUTE_PERFORMANCE) and the trip log")

cats = query(Q.ROUTE_CATEGORIES)
f1, f2 = st.columns([3, 2])
search = f1.text_input("Search route code, name or stop", max_chars=40, placeholder="e.g. Hebbal or KIA")
cat = f2.selectbox("Route category", ["All"] + (cats["ROUTE_CATEGORY"].tolist() if not cats.empty else []))

where, params = ["1 = 1"], {}
if search.strip():
    where.append("(ROUTE_CODE ILIKE %(q)s OR ROUTE_NAME ILIKE %(q)s)")
    params["q"] = f"%{search.strip()}%"
if cat != "All":
    where.append("ROUTE_CATEGORY = %(cat)s")
    params["cat"] = cat
routes = query(f"""
SELECT ROUTE_ID, ROUTE_CODE, ROUTE_NAME, ROUTE_CATEGORY, DISTANCE_KM, DEPOT_NAME, ACTIVE_FLAG, TRIPS,
       COMPLETED_TRIPS, CANCELLED_TRIPS, PASSENGERS, REVENUE, REVENUE_PER_KM, AVG_DELAY_MIN, AVG_OCCUPANCY,
       REVENUE_RANK
FROM BMTC_DW.TRIP.V_ROUTE_PERFORMANCE WHERE {' AND '.join(where)} ORDER BY REVENUE_RANK""", params)

st.subheader(f"Routes ({len(routes)})")
show_table(routes, height=300)

if not routes.empty:
    st.subheader("Route information")
    choice = st.selectbox("Select a route", (routes["ROUTE_CODE"] + " - " + routes["ROUTE_NAME"]).tolist())
    r = routes[routes["ROUTE_CODE"] == choice.split(" - ")[0]].iloc[0]
    c = st.columns(5)
    c[0].metric("Category", r.ROUTE_CATEGORY)
    c[1].metric("Distance", f"{r.DISTANCE_KM} km")
    c[2].metric("Trips", num(r.TRIPS))
    c[3].metric("Passengers", num(r.PASSENGERS))
    c[4].metric("Revenue", money(r.REVENUE))
    if r.TRIPS == 0:
        st.info("This route is inactive and has no trips in the period.")
    else:
        daily = query("""SELECT DATE_TRUNC('WEEK', TRIP_DATE)::DATE AS WEEK, COUNT(*) AS TRIPS,
                                SUM(PASSENGER_COUNT) AS PASSENGERS, ROUND(AVG(DELAY_MINUTES), 1) AS AVG_DELAY
                         FROM BMTC_DW.TRIP.TRIP_DATA WHERE ROUTE_ID = %(rid)s GROUP BY 1 ORDER BY 1""",
                      {"rid": int(r.ROUTE_ID)})
        a, b = st.columns(2)
        with a:
            chart(daily, "line", "WEEK", "PASSENGERS", f"Weekly passengers - {r.ROUTE_CODE}", hover_data=["TRIPS"])
        with b:
            chart(daily, "line", "WEEK", "AVG_DELAY", f"Weekly average delay (min) - {r.ROUTE_CODE}")

st.divider()
st.subheader("Top and bottom routes")
metric = st.radio("Rank by", ["REVENUE", "PASSENGERS", "REVENUE_PER_KM", "AVG_DELAY_MIN"], horizontal=True)
ranked = query("""SELECT ROUTE_CODE, ROUTE_CATEGORY, REVENUE, PASSENGERS, REVENUE_PER_KM, AVG_DELAY_MIN
                  FROM BMTC_DW.TRIP.V_ROUTE_PERFORMANCE WHERE TRIPS > 0""")
if not ranked.empty:
    t, bt = st.columns(2)
    with t:
        chart(ranked.nlargest(10, metric), "bar", "ROUTE_CODE", metric, f"Top 10 routes by {metric}",
              horizontal=True, hover_data=["ROUTE_CATEGORY"])
    with bt:
        chart(ranked.nsmallest(10, metric), "bar", "ROUTE_CODE", metric, f"Bottom 10 routes by {metric}",
              horizontal=True, hover_data=["ROUTE_CATEGORY"])

st.divider()
st.subheader("Trip log")
g1, g2, g3 = st.columns(3)
start = g1.date_input("From", dt.date(2026, 10, 1), min_value=dt.date(2025, 11, 1), max_value=dt.date(2026, 10, 31))
end = g2.date_input("To", dt.date(2026, 10, 31), min_value=dt.date(2025, 11, 1), max_value=dt.date(2026, 10, 31))
status = g3.selectbox("Trip status", ["All", "COMPLETED", "CANCELLED", "BREAKDOWN"])
p = {"s": start, "e": end}
sql = """SELECT TRIP_ID, TRIP_DATE, START_HOUR, PERIOD, ROUTE_CODE, REGISTRATION_NO, BUS_TYPE, DEPOT_NAME,
                TRIP_STATUS, DELAY_MINUTES, PASSENGER_COUNT, OCCUPANCY_RATIO, TICKETS, REVENUE
         FROM BMTC_DW.TRIP.V_TRIP_DETAILS WHERE TRIP_DATE BETWEEN %(s)s AND %(e)s"""
if status != "All":
    sql += " AND TRIP_STATUS = %(st)s"
    p["st"] = status
trips = query(sql + " ORDER BY TRIP_DATE DESC, TRIP_ID DESC LIMIT 2000", p)
st.caption(f"{len(trips)} trips (max 2,000 shown)")
show_table(trips, height=320)
if not trips.empty:
    by_hour = trips.groupby("START_HOUR", as_index=False).agg(TRIPS=("TRIP_ID", "count"),
                                                              AVG_PASSENGERS=("PASSENGER_COUNT", "mean"))
    chart(by_hour, "bar", "START_HOUR", "AVG_PASSENGERS", "Average passengers per trip by departure hour",
          hover_data=["TRIPS"])
