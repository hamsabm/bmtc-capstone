import streamlit as st

from utils import queries as Q
from utils.db import execute, query
from utils.ui import chart, money, num, page, show_table

page("Bus Management", "Fleet register with utilisation, fuel and maintenance (BUS.V_BUS_SUMMARY)")

depots = query(Q.DEPOTS)
types = query(Q.BUS_TYPES)
f1, f2, f3, f4 = st.columns([2, 2, 1.5, 2])
sel_depots = f1.multiselect("Depot", depots["DEPOT_NAME"].tolist() if not depots.empty else [])
sel_types = f2.multiselect("Bus type", types["BUS_TYPE"].tolist() if not types.empty else [])
sel_status = f3.selectbox("Status", ["All", "ACTIVE", "UNDER_MAINTENANCE", "RETIRED"])
search = f4.text_input("Search registration / manufacturer", max_chars=30)

# Fixed SQL fragments + bound parameters only (no user text in the SQL string)
where, params = ["1 = 1"], {}
if sel_depots:
    names = {f"d{i}": v for i, v in enumerate(sel_depots)}
    where.append(f"DEPOT_NAME IN ({', '.join('%(' + k + ')s' for k in names)})")
    params.update(names)
if sel_types:
    tps = {f"t{i}": v for i, v in enumerate(sel_types)}
    where.append(f"BUS_TYPE IN ({', '.join('%(' + k + ')s' for k in tps)})")
    params.update(tps)
if sel_status != "All":
    where.append("STATUS = %(status)s")
    params["status"] = sel_status
if search.strip():
    where.append("(REGISTRATION_NO ILIKE %(q)s OR MANUFACTURER ILIKE %(q)s)")
    params["q"] = f"%{search.strip()}%"

buses = query(f"""
SELECT BUS_ID, REGISTRATION_NO, BUS_TYPE, FUEL_TYPE, MANUFACTURER, MANUFACTURE_YEAR, STATUS, DEPOT_NAME, ZONE,
       TRIPS, KM_OPERATED, PASSENGERS, KM_PER_UNIT, FUEL_COST, MAINTENANCE_JOBS, MAINTENANCE_COST,
       DOWNTIME_HOURS, LAST_SERVICE
FROM BMTC_DW.BUS.V_BUS_SUMMARY WHERE {' AND '.join(where)} ORDER BY BUS_ID""", params)

m = st.columns(4)
m[0].metric("Buses shown", num(len(buses)))
if not buses.empty:
    m[1].metric("Trips operated", num(buses["TRIPS"].sum()))
    m[2].metric("Maintenance cost", money(buses["MAINTENANCE_COST"].sum()))
    m[3].metric("Average age (years)", f"{(2026 - buses['MANUFACTURE_YEAR']).mean():.1f}")
show_table(buses, height=360)

if not buses.empty:
    c1, c2 = st.columns(2)
    with c1:
        by_depot = buses.groupby("DEPOT_NAME", as_index=False).agg(BUSES=("BUS_ID", "count"),
                                                                    TRIPS=("TRIPS", "sum"))
        chart(by_depot, "bar", "DEPOT_NAME", "BUSES", "Depot analysis - buses", horizontal=True,
              hover_data=["TRIPS"])
    with c2:
        by_type = buses.groupby("BUS_TYPE", as_index=False).agg(BUSES=("BUS_ID", "count"),
                                                                 AVG_KM=("KM_OPERATED", "mean"))
        chart(by_type, "bar", "BUS_TYPE", "BUSES", "Bus type analysis", horizontal=True, hover_data=["AVG_KM"])
    chart(buses, "scatter", "MANUFACTURE_YEAR", "MAINTENANCE_COST",
          "Maintenance cost vs manufacture year (older buses cost more)", color="BUS_TYPE",
          hover_data=["REGISTRATION_NO", "DEPOT_NAME"])

st.divider()
st.subheader("Change bus status")
st.caption("Runs UPDATE BUS.BUS_MASTER and INSERT into BUS.BUS_STATUS_AUDIT in one transaction "
           "(rolled back if either fails).")
all_buses = query("SELECT BUS_ID, REGISTRATION_NO, STATUS FROM BMTC_DW.BUS.BUS_MASTER ORDER BY REGISTRATION_NO")
if not all_buses.empty:
    with st.form("status_form", clear_on_submit=True):
        a, b, c = st.columns([2, 1.5, 3])
        label = a.selectbox("Bus", (all_buses["REGISTRATION_NO"] + "  [" + all_buses["STATUS"] + "]").tolist())
        new_status = b.selectbox("New status", ["ACTIVE", "UNDER_MAINTENANCE", "RETIRED"])
        reason = c.text_input("Reason", max_chars=150, placeholder="e.g. Accident damage, sent to workshop")
        submitted = st.form_submit_button("Update status")
    if submitted:
        reg = label.split("  [")[0]
        row = all_buses[all_buses["REGISTRATION_NO"] == reg].iloc[0]
        if not reason.strip():
            st.error("Please enter a reason.")
        elif row.STATUS == new_status:
            st.info(f"{reg} is already {new_status}.")
        else:
            try:
                execute([
                    ("INSERT INTO BMTC_DW.BUS.BUS_STATUS_AUDIT (BUS_ID, OLD_STATUS, NEW_STATUS, REASON, CHANGE_SOURCE) "
                     "VALUES (%(id)s, %(old)s, %(new)s, %(reason)s, 'STREAMLIT_APP')",
                     {"id": int(row.BUS_ID), "old": row.STATUS, "new": new_status, "reason": reason.strip()}),
                    ("UPDATE BMTC_DW.BUS.BUS_MASTER SET STATUS = %(new)s WHERE BUS_ID = %(id)s",
                     {"new": new_status, "id": int(row.BUS_ID)}),
                ])
                st.success(f"{reg}: {row.STATUS} -> {new_status} (committed).")
                st.toast(f"{reg} is now {new_status}", icon=":material/check_circle:")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Update rolled back: {exc}")

st.markdown("**Recent status changes**")
show_table(query("""SELECT a.CHANGED_AT, b.REGISTRATION_NO, a.OLD_STATUS, a.NEW_STATUS, a.REASON, a.CHANGE_SOURCE
                    FROM BMTC_DW.BUS.BUS_STATUS_AUDIT a JOIN BMTC_DW.BUS.BUS_MASTER b ON b.BUS_ID = a.BUS_ID
                    ORDER BY a.CHANGED_AT DESC LIMIT 20""", cache=False), "No status changes recorded yet.")
