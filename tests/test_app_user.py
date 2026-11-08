r"""Least-privilege checks for the deployment identity BMTC_STREAMLIT_APP (role BMTC_APP, key-pair auth).
Run (PowerShell):
  $env:SNOWFLAKE_USER="BMTC_STREAMLIT_APP"; $env:SNOWFLAKE_ROLE="BMTC_APP"
  $env:SNOWFLAKE_PRIVATE_KEY_FILE="secrets/bmtc_app_rsa_key.p8"; $env:SNOWFLAKE_PASSWORD=""
  venv\Scripts\python.exe tests\test_app_user.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.snowflake_connection import connect, settings  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def denied(cur, sql):
    try:
        cur.execute(sql)
        return False
    except Exception:  # noqa: BLE001
        return True


cfg = settings()
check("Configured for key-pair auth, no password", cfg.get("authenticator") == "SNOWFLAKE_JWT" and "password" not in cfg)
conn = connect()
cur = conn.cursor()
cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()")
user, role, sec = cur.fetchone()
check("Connected as limited user", user == "BMTC_STREAMLIT_APP" and role == "BMTC_APP", f"{user} / {role}")

# Cannot reach admin privileges
check("Cannot USE ROLE ACCOUNTADMIN", denied(cur, "USE ROLE ACCOUNTADMIN"))
check("Cannot USE ROLE SYSADMIN", denied(cur, "USE ROLE SYSADMIN"))
cur.execute("SHOW GRANTS TO USER BMTC_STREAMLIT_APP")
cols = [d[0].lower() for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]
granted = {r.get("role") or r.get("name") for r in rows if (r.get("granted_on") or "ROLE") == "ROLE"}
check("Only BMTC_APP granted to the user", granted == {"BMTC_APP"}, ", ".join(sorted(granted)))
check("Cannot CREATE USER", denied(cur, "CREATE USER BMTC_SHOULD_NOT_EXIST"))
check("Cannot GRANT roles", denied(cur, "GRANT ROLE BMTC_ADMIN TO ROLE BMTC_APP"))
check("Cannot DROP project table", denied(cur, "DROP TABLE BMTC_DW.TRIP.TICKET_DATA"))
check("Cannot DELETE tickets", denied(cur, "DELETE FROM BMTC_DW.TRIP.TICKET_DATA WHERE 1 = 0"))
check("Cannot ALTER warehouse size", denied(cur, "ALTER WAREHOUSE BMTC_WH SET WAREHOUSE_SIZE = 'LARGE'"))
check("Cannot read account usage", denied(cur, "SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY"))

# PII protected
cur.execute("SELECT PHONE, EMAIL, PASSENGER_NAME FROM BMTC_DW.PASSENGER.PASS_DATA WHERE EMAIL IS NOT NULL LIMIT 1")
ph, em, nm = cur.fetchone()
check("Pass PII masked for the app", ph.startswith("XXXXXX") and em.startswith("*****@") and nm.endswith("*****"))
cur.execute("SELECT COUNT(MONTHLY_SALARY) FROM BMTC_DW.BUS.EMPLOYEE_MASTER")
check("Individual salaries hidden", cur.fetchone()[0] == 0)

# What the app needs
cur.execute("SELECT TOTAL_BUSES, TOTAL_TRIPS FROM BMTC_DW.TRIP.V_DASHBOARD_KPIS")
b, t = cur.fetchone()
check("Reads dashboard KPI view", b == 120 and t > 0, f"buses {b}, trips {t}")
cur.execute("SELECT COUNT(DISTINCT DEPOT_ID) FROM BMTC_DW.BUS.EMPLOYEE_MASTER")
check("Row access policy lets the app see all depots", cur.fetchone()[0] == 10)
for sql, name in [("SELECT SYSTEM$PIPE_STATUS('BMTC_DW.STAGING.PIPE_COMPLAINTS_FEED')", "pipe status"),
                  ("SELECT SYSTEM$STREAM_HAS_DATA('BMTC_DW.TRIP.TRIP_DATA_STREAM')", "stream status"),
                  ("SELECT BMTC_DW.TRIP.FUEL_EFFICIENCY_CLASS('Ordinary', 340, 100)", "Python UDF")]:
    check(f"Can read {name}", not denied(cur, sql))
conn.close()

print(f"\n{sum(results)}/{len(results)} limited-user checks passed")
sys.exit(0 if all(results) else 1)
