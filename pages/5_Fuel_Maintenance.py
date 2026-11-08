import datetime as dt

import streamlit as st

from utils import queries as Q
from utils.db import execute, query
from utils.ui import chart, money, num, page, show_table

page("Fuel & Maintenance", "Fuel efficiency (Python UDF classification) and workshop history")

depots = query(Q.DEPOTS)
depot_names = depots["DEPOT_NAME"].tolist() if not depots.empty else []
sel_depot = st.selectbox("Depot filter", ["All depots"] + depot_names)
dparams = {} if sel_depot == "All depots" else {"depot": sel_depot}
dwhere = "" if not dparams else " AND DEPOT_NAME = %(depot)s"

fuel_tab, maint_tab = st.tabs(["Fuel", "Maintenance"])

with fuel_tab:
    fuel = query(f"""SELECT * FROM BMTC_DW.TRIP.V_FUEL_EFFICIENCY_CLASSIFIED WHERE 1 = 1{dwhere}
                     ORDER BY FUEL_DATE DESC""", dparams)
    if fuel.empty:
        st.info("No fuel records for this selection.")
    else:
        c = st.columns(4)
        diesel = fuel[fuel["UNIT"] == "LITRE"]
        ev = fuel[fuel["UNIT"] == "KWH"]
        c[0].metric("Fuel / charging events", num(len(fuel)))
        c[1].metric("Diesel used", f"{num(diesel['QUANTITY'].sum())} L")
        c[2].metric("EV energy", f"{num(ev['QUANTITY'].sum())} kWh")
        c[3].metric("Energy cost", money(fuel["TOTAL_COST"].sum()))

        monthly = fuel.groupby(["FUEL_MONTH", "FUEL_TYPE"], as_index=False)["QUANTITY"].sum()
        a, b = st.columns(2)
        with a:
            chart(monthly[monthly["FUEL_TYPE"] == "Diesel"], "bar", "FUEL_MONTH", "QUANTITY",
                  "Diesel consumption per month (litres)")
        with b:
            chart(monthly[monthly["FUEL_TYPE"] == "Electric"], "bar", "FUEL_MONTH", "QUANTITY",
                  "EV charging per month (kWh)")
        a, b = st.columns(2)
        with a:
            chart(fuel, "box", "BUS_TYPE", "KM_PER_UNIT", "Fuel efficiency by bus type (km per L / kWh)")
        with b:
            cls = fuel.groupby(["BUS_TYPE", "EFFICIENCY_CLASS"], as_index=False).size().rename(columns={"size": "FILLS"})
            chart(cls, "bar", "BUS_TYPE", "FILLS", "Python UDF efficiency class per bus type",
                  color="EFFICIENCY_CLASS", category_orders={"EFFICIENCY_CLASS": ["EXCELLENT", "GOOD", "AVERAGE", "POOR"]})

        st.markdown("**Bus-wise fuel efficiency** (lowest first)")
        buswise = (fuel.groupby(["REGISTRATION_NO", "BUS_TYPE", "DEPOT_NAME", "UNIT"], as_index=False)
                   .agg(FILLS=("FUEL_ID", "count"), KM=("KM_SINCE_LAST_FILL", "sum"), QTY=("QUANTITY", "sum"),
                        COST=("TOTAL_COST", "sum"), POOR_FILLS=("EFFICIENCY_CLASS", lambda s: (s == "POOR").sum())))
        buswise["KM_PER_UNIT"] = (buswise["KM"] / buswise["QTY"]).round(2)
        buswise["COST_PER_KM"] = (buswise["COST"] / buswise["KM"]).round(2)
        show_table(buswise.sort_values(["BUS_TYPE", "KM_PER_UNIT"]), height=280)

        st.markdown("**Depot-wise energy cost per km**")
        dep = fuel.groupby(["DEPOT_NAME"], as_index=False).agg(COST=("TOTAL_COST", "sum"), KM=("KM_SINCE_LAST_FILL", "sum"))
        dep["COST_PER_KM"] = (dep["COST"] / dep["KM"]).round(2)
        chart(dep, "bar", "DEPOT_NAME", "COST_PER_KM", "Energy cost per km by depot (Rs)", horizontal=True)

with maint_tab:
    m1, m2 = st.columns(2)
    sev = m1.multiselect("Severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    mtype_df = query("SELECT DISTINCT MAINTENANCE_TYPE FROM BMTC_DW.TRIP.MAINTENANCE_LOG ORDER BY 1")
    mtypes = m2.multiselect("Maintenance type", mtype_df["MAINTENANCE_TYPE"].tolist() if not mtype_df.empty else [])
    p = dict(dparams)
    w = "1 = 1" + dwhere
    if sev:
        p.update({f"s{i}": v for i, v in enumerate(sev)})
        w += f" AND SEVERITY IN ({', '.join('%(s' + str(i) + ')s' for i in range(len(sev)))})"
    if mtypes:
        p.update({f"m{i}": v for i, v in enumerate(mtypes)})
        w += f" AND MAINTENANCE_TYPE IN ({', '.join('%(m' + str(i) + ')s' for i in range(len(mtypes)))})"
    maint = query(f"SELECT * FROM BMTC_DW.TRIP.V_MAINTENANCE_DETAILS WHERE {w} ORDER BY MAINTENANCE_DATE DESC", p)
    if maint.empty:
        st.info("No maintenance records for this selection.")
    else:
        c = st.columns(4)
        c[0].metric("Jobs", num(len(maint)))
        c[1].metric("Total cost", money(maint["TOTAL_COST"].sum()))
        c[2].metric("Downtime", f"{num(maint['DOWNTIME_HOURS'].sum())} h")
        c[3].metric("High / critical", num(maint["SEVERITY"].isin(["HIGH", "CRITICAL"]).sum()))
        a, b = st.columns(2)
        with a:
            freq = maint.groupby("MAINTENANCE_TYPE", as_index=False).agg(JOBS=("MAINTENANCE_ID", "count"),
                                                                         COST=("TOTAL_COST", "sum"))
            chart(freq, "bar", "MAINTENANCE_TYPE", "JOBS", "Maintenance frequency by type", horizontal=True,
                  hover_data=["COST"])
        with b:
            mon = maint.groupby("MAINTENANCE_MONTH", as_index=False)["TOTAL_COST"].sum()
            chart(mon, "bar", "MAINTENANCE_MONTH", "TOTAL_COST", "Maintenance cost per month (Rs)")
        a, b = st.columns(2)
        with a:
            dep = maint.groupby("DEPOT_NAME", as_index=False).agg(JOBS=("MAINTENANCE_ID", "count"),
                                                                  COST=("TOTAL_COST", "sum"))
            chart(dep, "bar", "DEPOT_NAME", "COST", "Maintenance cost by depot (Rs)", horizontal=True, hover_data=["JOBS"])
        with b:
            bus = maint.groupby(["REGISTRATION_NO", "BUS_TYPE"], as_index=False).agg(
                JOBS=("MAINTENANCE_ID", "count"), COST=("TOTAL_COST", "sum")).nlargest(10, "COST")
            chart(bus, "bar", "REGISTRATION_NO", "COST", "10 costliest buses to maintain (Rs)", horizontal=True,
                  hover_data=["JOBS", "BUS_TYPE"])
        st.markdown("**Maintenance history**")
        show_table(maint[["MAINTENANCE_DATE", "REGISTRATION_NO", "BUS_TYPE", "DEPOT_NAME", "MAINTENANCE_TYPE",
                          "DESCRIPTION", "SEVERITY", "TOTAL_COST", "DOWNTIME_HOURS", "MECHANIC_NAME", "STATUS"]],
                   height=300)

    st.divider()
    st.subheader("Log a workshop job")
    st.caption("Inserts a row into TRIP.MAINTENANCE_LOG (parameterised INSERT).")
    blist = query("SELECT BUS_ID, REGISTRATION_NO, DEPOT_ID FROM BMTC_DW.BUS.BUS_MASTER ORDER BY REGISTRATION_NO")
    if not blist.empty:
        with st.form("maint_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            reg = a.selectbox("Bus", blist["REGISTRATION_NO"].tolist())
            mtype = b.selectbox("Type", ["Preventive Service", "Brake Repair", "Tyre Replacement", "Engine Repair",
                                         "Electrical Fault", "AC Repair", "Battery Service", "Body Work"])
            severity = c.selectbox("Severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            a, b, c, d = st.columns(4)
            mdate = a.date_input("Date", dt.date(2026, 10, 31))
            parts = b.number_input("Parts cost (Rs)", 0.0, 500000.0, 2000.0, step=100.0)
            labour = c.number_input("Labour cost (Rs)", 0.0, 200000.0, 800.0, step=100.0)
            down = d.number_input("Downtime (hours)", 0.0, 500.0, 4.0, step=0.5)
            desc = st.text_input("Description", max_chars=180)
            ok = st.form_submit_button("Save job")
        if ok:
            bus_id = int(blist.loc[blist["REGISTRATION_NO"] == reg, "BUS_ID"].iloc[0])
            try:
                execute([("""INSERT INTO BMTC_DW.TRIP.MAINTENANCE_LOG
                    (MAINTENANCE_ID, BUS_ID, MAINTENANCE_DATE, MAINTENANCE_TYPE, DESCRIPTION, PARTS_COST, LABOUR_COST,
                     TOTAL_COST, DOWNTIME_HOURS, SEVERITY, MECHANIC_ID, STATUS)
                    SELECT COALESCE(MAX(MAINTENANCE_ID), 0) + 1, %(bus)s, %(d)s, %(t)s, %(desc)s, %(p)s, %(l)s,
                           %(p)s + %(l)s, %(h)s, %(sev)s, NULL, 'IN_PROGRESS'
                    FROM BMTC_DW.TRIP.MAINTENANCE_LOG""",
                          {"bus": bus_id, "d": mdate, "t": mtype, "desc": desc.strip() or mtype, "p": parts,
                           "l": labour, "h": down, "sev": severity})])
                st.success(f"Job saved for {reg}.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not save: {exc}")
