import datetime as dt

import streamlit as st

from utils import queries as Q
from utils.db import query
from utils.ui import chart, money, num, page, show_table

page("Ticket Analytics", "Ticket and pass-validation transactions (TRIP.TICKET_DATA)")

cats = query(Q.ROUTE_CATEGORIES)
f1, f2, f3 = st.columns(3)
start = f1.date_input("From", dt.date(2025, 11, 1), min_value=dt.date(2025, 11, 1), max_value=dt.date(2026, 10, 31))
end = f2.date_input("To", dt.date(2026, 10, 31), min_value=dt.date(2025, 11, 1), max_value=dt.date(2026, 10, 31))
cat = f3.selectbox("Route category", ["All"] + (cats["ROUTE_CATEGORY"].tolist() if not cats.empty else []))
if start > end:
    st.error("'From' must be before 'To'.")
    st.stop()

params = {"s": start, "e": end}
cat_filter = ""
if cat != "All":
    cat_filter = " AND r.ROUTE_CATEGORY = %(cat)s"
    params["cat"] = cat
BASE = f"""FROM BMTC_DW.TRIP.TICKET_DATA t JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
           WHERE t.TICKET_DATE BETWEEN %(s)s AND %(e)s{cat_filter}"""

tot = query(f"""SELECT COUNT(*) AS TICKETS, SUM(t.FARE) AS REVENUE, AVG(NULLIF(t.FARE, 0)) AS AVG_FARE,
                       COUNT_IF(t.PASS_ID IS NOT NULL) AS PASS_RIDES {BASE}""", params)
if not tot.empty:
    k = tot.iloc[0]
    c = st.columns(4)
    c[0].metric("Tickets / boardings", num(k.TICKETS))
    c[1].metric("Revenue", money(k.REVENUE))
    c[2].metric("Average paid fare", money(k.AVG_FARE))
    c[3].metric("Pass validations", f"{(k.PASS_RIDES / k.TICKETS * 100) if k.TICKETS else 0:.1f}%")

daily = query(f"""SELECT t.TICKET_DATE, COUNT(*) AS TICKETS, SUM(t.FARE) AS REVENUE {BASE}
                  GROUP BY 1 ORDER BY 1""", params)
if not daily.empty:
    daily["TICKETS_7D_AVG"] = daily["TICKETS"].rolling(7, min_periods=1).mean().round(1)
chart(daily, "line", "TICKET_DATE", "TICKETS_7D_AVG", "Daily tickets (7-day moving average)", hover_data=["TICKETS", "REVENUE"])

a, b = st.columns(2)
with a:
    chart(query(f"""SELECT t.PAYMENT_MODE, COUNT(*) AS TICKETS, SUM(t.FARE) AS REVENUE {BASE}
                    GROUP BY 1 ORDER BY 2 DESC""", params),
          "bar", "PAYMENT_MODE", "TICKETS", "Tickets by payment mode", horizontal=True, hover_data=["REVENUE"])
with b:
    chart(query(f"""SELECT t.PASSENGER_CATEGORY, COUNT(*) AS TICKETS, SUM(t.FARE) AS REVENUE {BASE}
                    GROUP BY 1 ORDER BY 2 DESC""", params),
          "bar", "PASSENGER_CATEGORY", "TICKETS", "Tickets by passenger category", horizontal=True,
          hover_data=["REVENUE"])

c1, c2 = st.columns(2)
with c1:
    chart(query(f"""SELECT HOUR(t.TICKET_TS) AS HOUR, COUNT(*) AS TICKETS {BASE} GROUP BY 1 ORDER BY 1""", params),
          "bar", "HOUR", "TICKETS", "Boardings by hour of day")
with c2:
    chart(query(f"""SELECT DAYNAME(t.TICKET_DATE) AS WEEKDAY, DAYOFWEEKISO(t.TICKET_DATE) AS D, COUNT(*) AS TICKETS
                    {BASE} GROUP BY 1, 2 ORDER BY 2""", params),
          "bar", "WEEKDAY", "TICKETS", "Boardings by weekday")

st.subheader("Route-wise ticket analysis")
routewise = query(f"""
SELECT r.ROUTE_CODE, r.ROUTE_CATEGORY, COUNT(*) AS TICKETS, SUM(t.FARE) AS REVENUE,
       ROUND(AVG(NULLIF(t.FARE, 0)), 1) AS AVG_FARE, ROUND(AVG(t.TRAVEL_KM), 1) AS AVG_TRAVEL_KM,
       ROUND(100 * COUNT_IF(t.PAYMENT_MODE = 'UPI') / COUNT(*), 1) AS UPI_SHARE_PCT,
       RANK() OVER (ORDER BY SUM(t.FARE) DESC) AS REVENUE_RANK
{BASE} GROUP BY r.ROUTE_CODE, r.ROUTE_CATEGORY ORDER BY REVENUE_RANK""", params)
chart(routewise.head(20), "bar", "ROUTE_CODE", "REVENUE", "Revenue by route (top 20)", color="ROUTE_CATEGORY",
      hover_data=["TICKETS", "AVG_FARE"], height=400)
show_table(routewise, height=300)

st.subheader("Monthly trend by route category")
chart(query(f"""SELECT DATE_TRUNC('MONTH', t.TICKET_DATE)::DATE AS MONTH, r.ROUTE_CATEGORY, SUM(t.FARE) AS REVENUE
                {BASE} GROUP BY 1, 2 ORDER BY 1""", params),
      "line", "MONTH", "REVENUE", "Monthly revenue by route category (Rs)", color="ROUTE_CATEGORY", markers=True)
