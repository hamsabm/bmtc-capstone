import datetime as dt
import json

import streamlit as st

from utils.db import execute, query
from utils.ui import chart, num, page, show_table

page("Passenger & Complaints",
     "Passes via secure view PASSENGER.SV_PASS_HOLDERS; complaints from JSON (VARIANT) documents")

pass_tab, comp_tab, new_tab = st.tabs(["Passenger passes", "Complaints", "Register a complaint"])

with pass_tab:
    st.caption("Personal data (name, phone, e-mail) is not exposed: this page reads the secure view.")
    f1, f2, f3 = st.columns(3)
    ptypes = query("SELECT DISTINCT PASS_TYPE FROM BMTC_DW.PASSENGER.SV_PASS_HOLDERS ORDER BY 1")
    ptype = f1.selectbox("Pass type", ["All"] + (ptypes["PASS_TYPE"].tolist() if not ptypes.empty else []))
    pstatus = f2.selectbox("Status", ["All", "ACTIVE", "EXPIRED", "CANCELLED"])
    pnum = f3.text_input("Pass number contains", max_chars=20)
    w, p = ["1 = 1"], {}
    if ptype != "All":
        w.append("PASS_TYPE = %(pt)s")
        p["pt"] = ptype
    if pstatus != "All":
        w.append("STATUS = %(ps)s")
        p["ps"] = pstatus
    if pnum.strip():
        w.append("PASS_NUMBER ILIKE %(pn)s")
        p["pn"] = f"%{pnum.strip()}%"
    passes = query(f"SELECT * FROM BMTC_DW.PASSENGER.SV_PASS_HOLDERS WHERE {' AND '.join(w)} ORDER BY ISSUE_DATE DESC", p)
    c = st.columns(3)
    c[0].metric("Passes", num(len(passes)))
    if not passes.empty:
        c[1].metric("Active", num((passes["STATUS"] == "ACTIVE").sum()))
        c[2].metric("Pass revenue", f"Rs {passes['PRICE'].sum():,.0f}")
        a, b = st.columns(2)
        with a:
            chart(passes.groupby("PASS_TYPE", as_index=False).size().rename(columns={"size": "PASSES"}),
                  "bar", "PASS_TYPE", "PASSES", "Passes by type", horizontal=True)
        with b:
            m = passes.assign(MONTH=passes["ISSUE_DATE"].map(lambda d: d.replace(day=1)))
            chart(m.groupby(["MONTH", "PASS_TYPE"], as_index=False).size().rename(columns={"size": "PASSES"}),
                  "bar", "MONTH", "PASSES", "Passes issued per month", color="PASS_TYPE")
    show_table(passes.head(500), height=300)

with comp_tab:
    cats = query("SELECT DISTINCT CATEGORY FROM BMTC_DW.PASSENGER.V_COMPLAINT_ANALYTICS ORDER BY 1")
    f1, f2, f3, f4 = st.columns(4)
    sel_cat = f1.multiselect("Category", cats["CATEGORY"].tolist() if not cats.empty else [])
    sel_pri = f2.multiselect("Priority", ["High", "Medium", "Low"])
    sel_st = f3.multiselect("Resolution status", ["Open", "In Progress", "Resolved", "Rejected"])
    since = f4.date_input("Submitted since", dt.date(2025, 11, 1))
    w, p = ["SUBMITTED_AT >= %(since)s"], {"since": since}
    for name, col, vals in (("c", "CATEGORY", sel_cat), ("p", "PRIORITY", sel_pri), ("r", "RESOLUTION_STATUS", sel_st)):
        if vals:
            keys = {f"{name}{i}": v for i, v in enumerate(vals)}
            w.append(f"{col} IN ({', '.join('%(' + k + ')s' for k in keys)})")
            p.update(keys)
    comp = query(f"SELECT * FROM BMTC_DW.PASSENGER.V_COMPLAINT_ANALYTICS WHERE {' AND '.join(w)} "
                 "ORDER BY SUBMITTED_AT DESC", p)
    c = st.columns(4)
    c[0].metric("Complaints", num(len(comp)))
    if not comp.empty:
        open_n = comp["RESOLUTION_STATUS"].isin(["Open", "In Progress"]).sum()
        c[1].metric("Open / in progress", num(open_n))
        c[2].metric("Avg resolution (days)", f"{comp['RESOLUTION_DAYS'].mean():.1f}")
        c[3].metric("Avg satisfaction (1-5)", f"{comp['SATISFACTION_RATING'].mean():.2f}")
        a, b = st.columns(2)
        with a:
            cat_df = comp.groupby(["CATEGORY", "PRIORITY"], as_index=False).size().rename(columns={"size": "COMPLAINTS"})
            chart(cat_df, "bar", "CATEGORY", "COMPLAINTS", "Complaint categories by priority", color="PRIORITY",
                  horizontal=True, category_orders={"PRIORITY": ["High", "Medium", "Low"]})
        with b:
            trend = comp.groupby("COMPLAINT_MONTH", as_index=False).size().rename(columns={"size": "COMPLAINTS"})
            chart(trend, "line", "COMPLAINT_MONTH", "COMPLAINTS", "Complaint trend per month", markers=True)
        a, b = st.columns(2)
        with a:
            chart(comp.groupby("CHANNEL", as_index=False).size().rename(columns={"size": "COMPLAINTS"}),
                  "bar", "CHANNEL", "COMPLAINTS", "Complaints by channel", horizontal=True)
        with b:
            chart(comp.groupby("DEPOT_NAME", as_index=False).size().rename(columns={"size": "COMPLAINTS"}),
                  "bar", "DEPOT_NAME", "COMPLAINTS", "Complaints by depot", horizontal=True)
        show_table(comp[["COMPLAINT_ID", "SUBMITTED_AT", "CATEGORY", "SUB_CATEGORY", "PRIORITY", "CHANNEL",
                         "ROUTE_CODE", "DEPOT_NAME", "STOP_NAME", "RESOLUTION_STATUS", "RESOLUTION_DAYS", "TAGS",
                         "INGESTION"]], height=300)

    st.subheader("Triage queue (Python UDF urgency score)")
    triage = query("""SELECT COMPLAINT_ID, SUBMITTED_AT, PAYLOAD:category::VARCHAR AS CATEGORY,
                             PAYLOAD:priority::VARCHAR AS PRIORITY, PAYLOAD:service.route_code::VARCHAR AS ROUTE,
                             ARRAY_TO_STRING(PAYLOAD:tags, ', ') AS TAGS,
                             PASSENGER.COMPLAINT_URGENCY_SCORE(PAYLOAD) AS URGENCY
                      FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON
                      WHERE PASSENGER.COMPLAINT_URGENCY_SCORE(PAYLOAD) > 0
                      ORDER BY URGENCY DESC, SUBMITTED_AT LIMIT 25""")
    show_table(triage, "No open complaints.")
    with st.expander("Inspect a raw JSON document"):
        cid = st.text_input("Complaint ID", "CMP-000001", max_chars=12)
        doc = query("SELECT PAYLOAD FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON WHERE COMPLAINT_ID = %(id)s", {"id": cid})
        if doc.empty:
            st.info("No complaint with that ID.")
        else:
            st.json(json.loads(doc.iloc[0]["PAYLOAD"]))

with new_tab:
    st.caption("Builds a JSON document and stores it in the VARIANT column PASSENGER.COMPLAINTS_JSON.PAYLOAD "
               "via PARSE_JSON (bound parameter).")
    trips = query("""SELECT t.TRIP_ID, r.ROUTE_ID, r.ROUTE_CODE, t.BUS_ID, b.DEPOT_ID, t.TRIP_DATE
                     FROM BMTC_DW.TRIP.TRIP_DATA t JOIN BMTC_DW.TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
                     JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = t.BUS_ID
                     WHERE t.TRIP_DATE >= '2026-10-25' ORDER BY t.TRIP_DATE DESC, t.TRIP_ID DESC LIMIT 300""")
    if trips.empty:
        st.info("No recent trips available.")
    else:
        with st.form("complaint_form", clear_on_submit=True):
            a, b = st.columns(2)
            trip_label = a.selectbox("Trip", (trips["TRIP_DATE"].astype(str) + " | trip " + trips["TRIP_ID"].astype(str)
                                              + " | route " + trips["ROUTE_CODE"]).tolist())
            category = b.selectbox("Category", ["Delay", "Overcrowding", "Staff Behaviour", "Ticketing", "Cleanliness",
                                                "Safety", "Bus Condition", "AC Not Working"])
            a, b, c = st.columns(3)
            priority = a.selectbox("Priority", ["Low", "Medium", "High"])
            channel = b.selectbox("Channel", ["Mobile App", "Helpline 1800-425-1663", "Depot Counter", "Email"])
            pass_id = c.number_input("Pass ID (optional, 0 = none)", 0, 9_999_999, 0)
            tags = st.multiselect("Tags", ["peak-hour", "repeat", "women-safety", "senior-citizen", "student", "night"])
            desc = st.text_area("Description", max_chars=300)
            send = st.form_submit_button("Submit complaint")
        if send:
            if not desc.strip():
                st.error("Please describe the complaint.")
            else:
                trip_id = int(trip_label.split(" | ")[1].replace("trip ", ""))
                t = trips[trips["TRIP_ID"] == trip_id].iloc[0]
                nxt = query("SELECT COALESCE(MAX(TRY_TO_NUMBER(SPLIT_PART(COMPLAINT_ID, '-', 2))), 0) + 1 AS N "
                            "FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON", cache=False)
                cid = f"CMP-{int(nxt.iloc[0]['N']):06d}"
                now = dt.datetime.now().replace(microsecond=0)
                doc = {"complaint_id": cid, "submitted_at": now.strftime("%Y-%m-%d %H:%M:%S"), "channel": channel,
                       "category": category, "sub_category": category, "priority": priority,
                       "description": desc.strip(),
                       "passenger": {"pass_id": int(pass_id) or None, "is_registered": bool(pass_id),
                                     "language": "English"},
                       "service": {"trip_id": int(t.TRIP_ID), "route_id": int(t.ROUTE_ID), "route_code": t.ROUTE_CODE,
                                   "bus_id": int(t.BUS_ID), "depot_id": int(t.DEPOT_ID), "trip_date": str(t.TRIP_DATE)},
                       "location": {"stop_name": None, "geo": None}, "tags": sorted(tags),
                       "resolution": {"status": "Open", "assigned_to": {"depot_id": int(t.DEPOT_ID), "employee_id": None},
                                      "resolution_days": None, "resolved_at": None, "satisfaction_rating": None}}
                try:
                    execute([("""INSERT INTO BMTC_DW.PASSENGER.COMPLAINTS_JSON (COMPLAINT_ID, SUBMITTED_AT, PAYLOAD, SOURCE_FILE)
                                 SELECT %(id)s, %(ts)s, PARSE_JSON(%(doc)s), 'APP'""",
                              {"id": cid, "ts": now, "doc": json.dumps(doc)})])
                    st.success(f"Complaint {cid} registered.")
                    st.json(doc)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not register complaint: {exc}")
