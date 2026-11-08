-- =====================================================================
-- 10_python_udf.sql | Python UDFs and a Python (Snowpark) stored procedure
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

-- UDF 1: fuel-efficiency class against a per-bus-type benchmark
-- Inputs: bus type, km driven since last fill, quantity (litres or kWh)
CREATE OR REPLACE FUNCTION TRIP.FUEL_EFFICIENCY_CLASS(BUS_TYPE VARCHAR, KM FLOAT, QUANTITY FLOAT)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
HANDLER = 'classify'
COMMENT = 'Classifies a fuel/charging event as EXCELLENT / GOOD / AVERAGE / POOR vs bus-type benchmark'
AS
$$
BENCHMARK = {            # expected km per litre (diesel) or km per kWh (electric)
    "Ordinary": 3.4, "Midi Feeder": 4.3, "Vajra AC": 2.4,
    "Vayu Vajra": 2.2, "Electric AC": 1.1,
}

def classify(bus_type, km, quantity):
    if not km or not quantity or quantity <= 0:
        return "UNKNOWN"
    ratio = (km / quantity) / BENCHMARK.get(bus_type, 3.0)
    if ratio >= 1.05:
        return "EXCELLENT"
    if ratio >= 0.95:
        return "GOOD"
    if ratio >= 0.85:
        return "AVERAGE"
    return "POOR"
$$;

-- UDF 2: complaint urgency score (0-100) from the JSON document
CREATE OR REPLACE FUNCTION PASSENGER.COMPLAINT_URGENCY_SCORE(DOC VARIANT)
RETURNS NUMBER
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
HANDLER = 'score'
COMMENT = 'Scores complaint urgency for triage using priority, category, tags and resolution state'
AS
$$
PRIORITY = {"High": 50, "Medium": 30, "Low": 10}
CATEGORY = {"Safety": 30, "Staff Behaviour": 15, "Delay": 10, "Overcrowding": 10, "AC Not Working": 8}
TAGS = {"women-safety": 20, "senior-citizen": 8, "repeat": 10, "night": 5}

def score(doc):
    if not isinstance(doc, dict):
        return 0
    status = (doc.get("resolution") or {}).get("status")
    if status in ("Resolved", "Rejected"):
        return 0
    s = PRIORITY.get(doc.get("priority"), 10) + CATEGORY.get(doc.get("category"), 5)
    s += sum(TAGS.get(t, 0) for t in (doc.get("tags") or []))
    return min(100, s)
$$;

-- Use the UDFs on project data
SELECT TRIP.FUEL_EFFICIENCY_CLASS('Ordinary', 340, 100)    AS EXPECT_GOOD,
       TRIP.FUEL_EFFICIENCY_CLASS('Electric AC', 150, 180) AS EXPECT_POOR,
       TRIP.FUEL_EFFICIENCY_CLASS('Vajra AC', 0, 0)        AS EXPECT_UNKNOWN;

CREATE OR REPLACE VIEW TRIP.V_FUEL_EFFICIENCY_CLASSIFIED
COMMENT = 'Fuel events with Python UDF efficiency class' AS
SELECT v.*, TRIP.FUEL_EFFICIENCY_CLASS(v.BUS_TYPE, v.KM_SINCE_LAST_FILL, v.QUANTITY) AS EFFICIENCY_CLASS
FROM TRIP.V_FUEL_EFFICIENCY v;

SELECT BUS_TYPE, EFFICIENCY_CLASS, COUNT(*) AS FILLS, ROUND(AVG(KM_PER_UNIT), 2) AS AVG_KM_PER_UNIT
FROM TRIP.V_FUEL_EFFICIENCY_CLASSIFIED GROUP BY BUS_TYPE, EFFICIENCY_CLASS ORDER BY BUS_TYPE, EFFICIENCY_CLASS;

SELECT COMPLAINT_ID, PAYLOAD:category::VARCHAR AS CATEGORY, PAYLOAD:priority::VARCHAR AS PRIORITY,
       PAYLOAD:resolution.status::VARCHAR AS STATUS, PASSENGER.COMPLAINT_URGENCY_SCORE(PAYLOAD) AS URGENCY
FROM PASSENGER.COMPLAINTS_JSON
WHERE PASSENGER.COMPLAINT_URGENCY_SCORE(PAYLOAD) > 0
ORDER BY URGENCY DESC, SUBMITTED_AT LIMIT 10;

-- Stored procedure (Python + Snowpark): writes a fleet-health snapshot per depot and
-- returns a short text summary. Used by the Data Management page.
CREATE TABLE IF NOT EXISTS TRIP.FLEET_HEALTH_SNAPSHOT (
  SNAPSHOT_AT TIMESTAMP_NTZ, DEPOT_NAME VARCHAR, BUSES NUMBER, POOR_EFFICIENCY_FILLS NUMBER,
  SERIOUS_MAINTENANCE_JOBS NUMBER, MAINTENANCE_COST NUMBER(14,2), HEALTH_SCORE NUMBER(5,1));

CREATE OR REPLACE PROCEDURE TRIP.SP_FLEET_HEALTH_SNAPSHOT()
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
COMMENT = 'Computes a 0-100 fleet health score per depot and stores a snapshot'
EXECUTE AS OWNER
AS
$$
def run(session):
    rows = session.sql("""
        WITH f AS (SELECT DEPOT_NAME, COUNT_IF(EFFICIENCY_CLASS = 'POOR') POOR, COUNT(*) FILLS
                   FROM BMTC_DW.TRIP.V_FUEL_EFFICIENCY_CLASSIFIED GROUP BY DEPOT_NAME),
             m AS (SELECT DEPOT_NAME, COUNT_IF(SEVERITY IN ('HIGH','CRITICAL')) SERIOUS, SUM(TOTAL_COST) COST,
                          COUNT(DISTINCT BUS_ID) BUSES
                   FROM BMTC_DW.TRIP.V_MAINTENANCE_DETAILS GROUP BY DEPOT_NAME)
        SELECT m.DEPOT_NAME, m.BUSES, COALESCE(f.POOR, 0) POOR, COALESCE(f.FILLS, 0) FILLS, m.SERIOUS, m.COST
        FROM m LEFT JOIN f ON f.DEPOT_NAME = m.DEPOT_NAME""").collect()
    out = []
    for r in rows:
        poor_rate = r["POOR"] / r["FILLS"] if r["FILLS"] else 0
        serious_per_bus = r["SERIOUS"] / r["BUSES"] if r["BUSES"] else 0
        score = max(0.0, 100 - 120 * poor_rate - 15 * serious_per_bus)
        out.append((r["DEPOT_NAME"], r["BUSES"], r["POOR"], r["SERIOUS"], float(r["COST"]), round(score, 1)))
    if not out:
        return "No data"
    import datetime
    now = datetime.datetime.utcnow().replace(microsecond=0)
    df = session.create_dataframe([(now,) + r for r in out],
                                  schema=["SNAPSHOT_AT", "DEPOT_NAME", "BUSES", "POOR_EFFICIENCY_FILLS",
                                          "SERIOUS_MAINTENANCE_JOBS", "MAINTENANCE_COST", "HEALTH_SCORE"])
    df.write.mode("append").save_as_table("BMTC_DW.TRIP.FLEET_HEALTH_SNAPSHOT", column_order="name")
    worst = min(out, key=lambda x: x[5])
    best = max(out, key=lambda x: x[5])
    return f"{len(out)} depots scored. Best: {best[0]} ({best[5]}). Needs attention: {worst[0]} ({worst[5]})."
$$;                                                                                   -- @optional

CALL TRIP.SP_FLEET_HEALTH_SNAPSHOT();                                                 -- @optional
SELECT DEPOT_NAME, BUSES, POOR_EFFICIENCY_FILLS, SERIOUS_MAINTENANCE_JOBS, HEALTH_SCORE
FROM TRIP.FLEET_HEALTH_SNAPSHOT
QUALIFY SNAPSHOT_AT = MAX(SNAPSHOT_AT) OVER () ORDER BY HEALTH_SCORE;

GRANT USAGE ON FUNCTION TRIP.FUEL_EFFICIENCY_CLASS(VARCHAR, FLOAT, FLOAT) TO ROLE BMTC_ANALYST;
GRANT USAGE ON FUNCTION PASSENGER.COMPLAINT_URGENCY_SCORE(VARIANT) TO ROLE BMTC_ANALYST;
GRANT SELECT ON VIEW TRIP.V_FUEL_EFFICIENCY_CLASSIFIED TO ROLE BMTC_ANALYST;
GRANT SELECT ON TABLE TRIP.FLEET_HEALTH_SNAPSHOT TO ROLE BMTC_ANALYST;
GRANT USAGE ON PROCEDURE TRIP.SP_FLEET_HEALTH_SNAPSHOT() TO ROLE BMTC_MANAGER;       -- @optional
