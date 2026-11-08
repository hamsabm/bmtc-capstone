r"""Interaction tests: filters, SQL-injection input, empty results, every advanced query, and the
three write forms (rows created by the test are removed afterwards).
Run: venv\Scripts\python.exe tests\test_interactions.py"""
from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contextlib import contextmanager  # noqa: E402

from dotenv import dotenv_values  # noqa: E402

from utils.snowflake_connection import run_query  # noqa: E402


@contextmanager
def admin_connection():
    """Verification/clean-up uses the owner's credentials from the .env FILE, independent of the
    (possibly limited) identity the app under test runs as."""
    import snowflake.connector
    v = dotenv_values(ROOT / ".env")
    conn = snowflake.connector.connect(account=v["SNOWFLAKE_ACCOUNT"], user=v["SNOWFLAKE_USER"],
                                       password=v["SNOWFLAKE_PASSWORD"], role=v.get("SNOWFLAKE_ROLE") or None,
                                       warehouse=v.get("SNOWFLAKE_WAREHOUSE", "BMTC_WH"), database="BMTC_DW")
    try:
        yield conn
    finally:
        conn.close()

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def page(p):
    at = AppTest.from_file(str(ROOT / "pages" / p), default_timeout=180)
    at.run()
    return at


def clean(at):
    return not at.exception and not at.error


# Bus search: normal, injection attempt, no-match
at = page("2_Bus_Management.py")
at.text_input[0].input("Volvo").run()
check("Bus search 'Volvo' returns rows", clean(at) and len(at.dataframe[0].value) > 0, f"{len(at.dataframe[0].value)} rows")
at.text_input[0].input("' OR 1=1 --").run()
check("Bus search with SQL-injection text is safe (0 rows, no error)", clean(at) and len(at.info) > 0)
at.multiselect[0].select("Hebbal Depot").run()
at.text_input[0].input("").run()
check("Bus depot filter", clean(at) and set(at.dataframe[0].value["DEPOT_NAME"]) == {"Hebbal Depot"})

# Routes search + route detail
at = page("3_Routes_Trips.py")
at.text_input[0].input("Airport").run()
check("Route search 'Airport'", clean(at) and len(at.dataframe[0].value) > 0, f"{len(at.dataframe[0].value)} routes")
at.text_input[0].input("no-such-route-xyz").run()
check("Route search with no match does not crash", clean(at))
at = page("3_Routes_Trips.py")
at.selectbox[2].select("CANCELLED").run() if len(at.selectbox) > 2 else None
check("Trip log status filter", clean(at))

# Ticket analytics: narrow range + category
at = page("4_Ticket_Analytics.py")
at.selectbox[0].select("Airport Vayu Vajra").run()
check("Ticket category filter", clean(at) and len(at.get("plotly_chart")) >= 5)

# Advanced analytics: every query
at = page("7_Advanced_Analytics.py")
for opt in at.selectbox[0].options:
    at.selectbox[0].select(opt).run()
    check(f"Advanced: {opt[:60]}", clean(at) and len(at.dataframe) == 1, f"{len(at.dataframe[0].value)} rows")

# Complaint filters
at = page("6_Passenger_Complaints.py")
at.multiselect[0].select("Safety").run()
check("Complaint category filter", clean(at))

# ---------------- write paths ----------------
with admin_connection() as conn:
    before = run_query(conn, """SELECT (SELECT COUNT(*) FROM BMTC_DW.TRIP.MAINTENANCE_LOG) M,
        (SELECT COUNT(*) FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON) C,
        (SELECT MAX(MAINTENANCE_ID) FROM BMTC_DW.TRIP.MAINTENANCE_LOG) MAXM""").iloc[0]
    bus = run_query(conn, "SELECT BUS_ID, REGISTRATION_NO, STATUS FROM BMTC_DW.BUS.BUS_MASTER WHERE STATUS='ACTIVE' ORDER BY REGISTRATION_NO LIMIT 1").iloc[0]

# 1) maintenance form
at = page("5_Fuel_Maintenance.py")
at.text_input(key=None) if False else None
desc_inputs = [t for t in at.text_input if t.label == "Description"]
desc_inputs[0].input("APP TEST job - auto-removed")
at.button[1].click() if False else None
form_btn = [b for b in at.button if b.label == "Save job"]
form_btn[0].click().run()
check("Maintenance form insert", clean(at) and any("Job saved" in s.value for s in at.success))

# 2) complaint form
at = page("6_Passenger_Complaints.py")
[t for t in at.text_area if t.label == "Description"][0].input("APP TEST complaint - auto-removed")
[b for b in at.button if b.label == "Submit complaint"][0].click().run()
check("Complaint form insert (JSON -> VARIANT)", clean(at) and any("registered" in s.value for s in at.success))

# 3) bus status change (transaction + audit)
at = page("2_Bus_Management.py")
[t for t in at.text_input if t.label == "Reason"][0].input("APP TEST - auto-reverted")
[s for s in at.selectbox if s.label == "New status"][0].select("UNDER_MAINTENANCE")
[b for b in at.button if b.label == "Update status"][0].click().run()
check("Bus status update (transaction)", clean(at) and any("committed" in s.value for s in at.success))

with admin_connection() as conn:
    after = run_query(conn, """SELECT (SELECT COUNT(*) FROM BMTC_DW.TRIP.MAINTENANCE_LOG) M,
        (SELECT COUNT(*) FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON) C,
        (SELECT STATUS FROM BMTC_DW.BUS.BUS_MASTER WHERE BUS_ID = %(b)s) S,
        (SELECT COUNT(*) FROM BMTC_DW.BUS.BUS_STATUS_AUDIT WHERE REASON LIKE 'APP TEST%%') A,
        (SELECT PAYLOAD:service.route_code::VARCHAR FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON WHERE SOURCE_FILE='APP' LIMIT 1) R""",
                      {"b": int(bus.BUS_ID)}).iloc[0]
    check("Rows really written to Snowflake", after.M == before.M + 1 and after.C == before.C + 1
          and after.S == "UNDER_MAINTENANCE" and after.A >= 1 and after.R is not None,
          f"maint {before.M}->{after.M}, complaints {before.C}->{after.C}, bus {bus.REGISTRATION_NO} {after.S}")
    # clean-up
    cur = conn.cursor()
    cur.execute("DELETE FROM BMTC_DW.TRIP.MAINTENANCE_LOG WHERE DESCRIPTION = 'APP TEST job - auto-removed'")
    cur.execute("DELETE FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON WHERE PAYLOAD:description::VARCHAR = 'APP TEST complaint - auto-removed'")
    cur.execute("UPDATE BMTC_DW.BUS.BUS_MASTER SET STATUS = %(s)s WHERE BUS_ID = %(b)s", {"s": bus.STATUS, "b": int(bus.BUS_ID)})
    cur.execute("DELETE FROM BMTC_DW.BUS.BUS_STATUS_AUDIT WHERE REASON LIKE 'APP TEST%%'")
    final = run_query(conn, """SELECT (SELECT COUNT(*) FROM BMTC_DW.TRIP.MAINTENANCE_LOG) M,
        (SELECT COUNT(*) FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON) C""").iloc[0]
    check("Test rows cleaned up", final.M == before.M and final.C == before.C)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} interaction checks passed")
sys.exit(1 if failed else 0)
