"""Final validation of the BMTC Snowflake build + credential hygiene.
Run: venv\\Scripts\\python.exe scripts\\validate.py
Prints PASS/FAIL per check; never prints secrets."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.snowflake_connection import connection, run_query  # noqa: E402

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


MIN_ROWS = {"BUS.BUS_MASTER": 50, "BUS.DEPOT_MASTER": 8, "BUS.EMPLOYEE_MASTER": 50, "TRIP.ROUTE_MASTER": 20,
            "TRIP.TRIP_DATA": 500, "TRIP.TICKET_DATA": 1000, "TRIP.FUEL_LOG": 300, "TRIP.MAINTENANCE_LOG": 200,
            "PASSENGER.PASS_DATA": 500, "PASSENGER.COMPLAINTS_JSON": 100}

with connection() as c:
    q = lambda sql, p=None: run_query(c, sql, p)  # noqa: E731
    wh = q("SHOW WAREHOUSES LIKE 'BMTC_WH'")
    check("Warehouse BMTC_WH exists", len(wh) == 1)
    if len(wh):
        w = wh.iloc[0]
        check("Warehouse XSMALL / auto-suspend 60 / auto-resume",
              str(w["size"]).upper().replace("-", "") == "XSMALL" and str(w["auto_suspend"]) == "60"
              and str(w["auto_resume"]).lower() == "true", f"{w['size']}, {w['auto_suspend']}s, {w['auto_resume']}")
        check("Resource monitor attached", str(w.get("resource_monitor", "")) == "BMTC_RM", str(w.get("resource_monitor")))
    check("Database BMTC_DW exists", len(q("SHOW DATABASES LIKE 'BMTC_DW'")) == 1)
    schemas = set(q("SHOW SCHEMAS IN DATABASE BMTC_DW")["name"])
    check("Schemas BUS/TRIP/PASSENGER (+STAGING, GOVERNANCE)",
          {"BUS", "TRIP", "PASSENGER", "STAGING", "GOVERNANCE"} <= schemas)
    for t, n in MIN_ROWS.items():
        cnt = int(q(f"SELECT COUNT(*) N FROM BMTC_DW.{t}").iloc[0]["N"])
        check(f"{t} rows >= {n}", cnt >= n, f"{cnt:,}")
    col = q("""SELECT DATA_TYPE FROM BMTC_DW.INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA='PASSENGER' AND TABLE_NAME='COMPLAINTS_JSON' AND COLUMN_NAME='PAYLOAD'""")
    check("COMPLAINTS_JSON.PAYLOAD is VARIANT", not col.empty and col.iloc[0]["DATA_TYPE"] == "VARIANT")
    kinds = q("""SELECT IS_TRANSIENT, COUNT(*) N FROM BMTC_DW.INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_TYPE='BASE TABLE' GROUP BY 1""")
    check("Permanent and transient tables present", set(kinds["IS_TRANSIENT"]) == {"YES", "NO"})
    views = q("SHOW VIEWS IN DATABASE BMTC_DW")
    views = views[views["schema_name"] != "INFORMATION_SCHEMA"]
    secure = views[views["is_secure"].astype(str).str.lower() == "true"]
    check("Standard views created", len(views) - len(secure) >= 8, f"{len(views) - len(secure)} standard")
    check("Secure views created", len(secure) >= 3, ", ".join(secure["name"]))
    mv = q("SHOW MATERIALIZED VIEWS IN DATABASE BMTC_DW")
    check("Materialized view exists", len(mv) >= 1, ", ".join(mv["name"]) if len(mv) else "")
    st = q("SHOW STREAMS IN DATABASE BMTC_DW")
    check("Stream TRIP_DATA_STREAM exists and is not stale",
          len(st) >= 1 and str(st.iloc[0]["stale"]).lower() == "false")
    tk = q("SHOW TASKS IN DATABASE BMTC_DW")
    check("Task exists and is started", len(tk) >= 1 and tk.iloc[0]["state"] == "started", tk.iloc[0]["state"] if len(tk) else "")
    hist = q("""SELECT COUNT_IF(STATE='SUCCEEDED') S, COUNT_IF(STATE='FAILED') F FROM TABLE(
                BMTC_DW.INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME=>'TASK_REFRESH_TRIP_SUMMARY'))""").iloc[0]
    check("Task has succeeded runs and no failures", hist.S >= 1 and hist.F == 0, f"{hist.S} succeeded, {hist.F} failed")
    check("Summary table reconciles with source",
          int(q("SELECT * FROM BMTC_DW.TRIP.V_SUMMARY_RECONCILIATION").iloc[0, 0]) == 0)
    check("Snowpipe exists", len(q("SHOW PIPES IN DATABASE BMTC_DW")) >= 1)
    check("Snowpipe loaded the feed file",
          int(q("SELECT COUNT(*) N FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON WHERE SOURCE_FILE LIKE 'feed/%'").iloc[0]["N"]) == 25)
    fn = q("SHOW USER FUNCTIONS IN DATABASE BMTC_DW")
    check("Python UDFs exist", {"FUEL_EFFICIENCY_CLASS", "COMPLAINT_URGENCY_SCORE"} <= set(fn["name"]))
    check("Python UDF returns expected value",
          q("SELECT BMTC_DW.TRIP.FUEL_EFFICIENCY_CLASS('Ordinary', 340, 100) R").iloc[0]["R"] == "GOOD")
    pr = q("SHOW PROCEDURES IN DATABASE BMTC_DW")
    check("Stored procedures exist (Python + SQL)",
          {"SP_FLEET_HEALTH_SNAPSHOT", "SP_APPLY_TRIP_CHANGES"} <= set(pr["name"]))
    roles = set(q("SHOW ROLES LIKE 'BMTC%'")["name"])
    check("Roles exist", {"BMTC_ADMIN", "BMTC_MANAGER", "BMTC_ANALYST", "BMTC_VIEWER"} <= roles)
    users = set(q("SHOW USERS LIKE 'BMTC%'")["name"])
    check("Demo users exist", len(users) >= 4, ", ".join(sorted(users)))
    pol = q("""SELECT POLICY_KIND, COUNT(*) N FROM TABLE(BMTC_DW.INFORMATION_SCHEMA.POLICY_REFERENCES(
               REF_ENTITY_NAME=>'BMTC_DW.BUS.EMPLOYEE_MASTER', REF_ENTITY_DOMAIN=>'table')) GROUP BY 1""")
    check("Masking + row access policies attached", set(pol["POLICY_KIND"]) == {"MASKING_POLICY", "ROW_ACCESS_POLICY"})
    check("Outbound share exists", len(q("SHOW SHARES LIKE 'BMTC_ROUTE_PERFORMANCE_SHARE'")) == 1)
    dups = q("""SELECT (SELECT COUNT(*) - COUNT(DISTINCT TRIP_ID) FROM BMTC_DW.TRIP.TRIP_DATA)
                     + (SELECT COUNT(*) - COUNT(DISTINCT TICKET_ID) FROM BMTC_DW.TRIP.TICKET_DATA)
                     + (SELECT COUNT(*) - COUNT(DISTINCT COMPLAINT_ID) FROM BMTC_DW.PASSENGER.COMPLAINTS_JSON) D""")
    check("No duplicate primary keys", int(dups.iloc[0]["D"]) == 0)

    # Least privilege, tested as the viewer role only
    cur = c.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    cur.execute("USE ROLE BMTC_VIEWER")
    try:
        cur.execute("SELECT COUNT(*) FROM BMTC_DW.TRIP.V_PBI_ROUTE_DAY_FACT")
        check("BMTC_VIEWER can read BI views", cur.fetchone()[0] > 0)
        try:
            cur.execute("SELECT * FROM BMTC_DW.PASSENGER.PASS_DATA LIMIT 1")
            check("BMTC_VIEWER blocked from PASS_DATA (PII)", False)
        except Exception:  # noqa: BLE001
            check("BMTC_VIEWER blocked from PASS_DATA (PII)", True)
    finally:
        cur.execute("USE ROLE ACCOUNTADMIN")
        cur.execute("USE SECONDARY ROLES ALL")

# Credential hygiene: the password must not appear in any project file other than .env
secret = os.getenv("SNOWFLAKE_PASSWORD", "")
leaks = []
if secret:
    for p in ROOT.rglob("*"):
        if p.is_file() and "venv" not in p.parts and p.name != ".env" and p.suffix not in (".pyc", ".gz"):
            try:
                if secret in p.read_text(encoding="utf-8", errors="ignore"):
                    leaks.append(str(p.relative_to(ROOT)))
            except OSError:
                pass
check("Password not present in any project file except .env", not leaks, ", ".join(leaks))
gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
check(".env is git-ignored", ".env" in gi.splitlines())

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} validation checks passed")
sys.exit(1 if failed else 0)
