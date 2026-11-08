-- =====================================================================
-- 07_time_travel_clone.sql | Time Travel + Zero-Copy Cloning on project data
-- Scenario: an operator applies a wrong fare revision to AC Vajra routes.
--   original data -> controlled (wrong) update -> query the past -> recover
-- The production table ends exactly as it started (verified below).
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

SHOW TABLES LIKE 'ROUTE_MASTER' IN SCHEMA TRIP;   -- retention_time column = Time Travel window (days)

-- 1. Original data
SELECT ROUTE_ID, ROUTE_CODE, ROUTE_CATEGORY, BASE_FARE FROM TRIP.ROUTE_MASTER
WHERE ROUTE_CATEGORY = 'AC Vajra' ORDER BY ROUTE_ID;
SET fare_checksum_before = (SELECT SUM(BASE_FARE) FROM TRIP.ROUTE_MASTER);

-- 2. Controlled change: wrong fare revision (x10 instead of +10%)
UPDATE TRIP.ROUTE_MASTER SET BASE_FARE = BASE_FARE * 10 WHERE ROUTE_CATEGORY = 'AC Vajra';
SET bad_update_qid = LAST_QUERY_ID();
SELECT ROUTE_ID, ROUTE_CODE, BASE_FARE AS FARE_AFTER_ERROR FROM TRIP.ROUTE_MASTER
WHERE ROUTE_CATEGORY = 'AC Vajra' ORDER BY ROUTE_ID;

-- 3. Time Travel query: the table as it was just before the bad statement
SELECT cur.ROUTE_CODE, old.BASE_FARE AS FARE_BEFORE, cur.BASE_FARE AS FARE_NOW
FROM TRIP.ROUTE_MASTER cur
JOIN TRIP.ROUTE_MASTER BEFORE (STATEMENT => $bad_update_qid) old ON old.ROUTE_ID = cur.ROUTE_ID
WHERE cur.BASE_FARE <> old.BASE_FARE ORDER BY cur.ROUTE_ID;

-- Point-in-time clone (Time Travel + cloning): snapshot of the correct fares kept for audit
CREATE OR REPLACE TABLE TRIP.ROUTE_MASTER_PRE_FARE_ERROR CLONE TRIP.ROUTE_MASTER BEFORE (STATEMENT => $bad_update_qid);

-- 4. Recovery from history
UPDATE TRIP.ROUTE_MASTER r SET BASE_FARE = h.BASE_FARE
FROM (SELECT ROUTE_ID, BASE_FARE FROM TRIP.ROUTE_MASTER BEFORE (STATEMENT => $bad_update_qid)) h
WHERE r.ROUTE_ID = h.ROUTE_ID AND r.BASE_FARE <> h.BASE_FARE;

SELECT $fare_checksum_before AS CHECKSUM_BEFORE, SUM(BASE_FARE) AS CHECKSUM_AFTER_RECOVERY,
       IFF($fare_checksum_before = SUM(BASE_FARE), 'RECOVERED', 'MISMATCH') AS RESULT
FROM TRIP.ROUTE_MASTER;

-- ============================ Zero-copy clone ========================
-- Dev/test copy of the fleet register: test a fleet-renewal rule without touching production
CREATE OR REPLACE TABLE BUS.BUS_MASTER_CLONE CLONE BUS.BUS_MASTER;
SELECT (SELECT COUNT(*) FROM BUS.BUS_MASTER) AS PROD_ROWS, (SELECT COUNT(*) FROM BUS.BUS_MASTER_CLONE) AS CLONE_ROWS;

-- Experiment on the clone only: retire diesel buses built before 2018
UPDATE BUS.BUS_MASTER_CLONE SET STATUS = 'RETIRED' WHERE FUEL_TYPE = 'Diesel' AND MANUFACTURE_YEAR < 2018;

SELECT 'PRODUCTION' AS COPY, STATUS, COUNT(*) AS BUSES FROM BUS.BUS_MASTER GROUP BY STATUS
UNION ALL
SELECT 'CLONE (renewal test)', STATUS, COUNT(*) FROM BUS.BUS_MASTER_CLONE GROUP BY STATUS
ORDER BY COPY, STATUS;

-- Impact of the experiment: seats lost per depot if those buses were retired
SELECT d.DEPOT_NAME, SUM(c.SEATING_CAPACITY) AS SEATS_TO_REPLACE, COUNT(*) AS BUSES_TO_REPLACE
FROM BUS.BUS_MASTER_CLONE c JOIN BUS.DEPOT_MASTER d ON d.DEPOT_ID = c.DEPOT_ID
WHERE c.STATUS = 'RETIRED' GROUP BY d.DEPOT_NAME ORDER BY SEATS_TO_REPLACE DESC;

-- Storage: a clone shares micro-partitions with its source until either side changes
SELECT TABLE_NAME, CLONE_GROUP_ID, ACTIVE_BYTES
FROM INFORMATION_SCHEMA.TABLE_STORAGE_METRICS
WHERE TABLE_SCHEMA = 'BUS' AND TABLE_NAME IN ('BUS_MASTER', 'BUS_MASTER_CLONE');          -- @optional

-- DROP / UNDROP (Time Travel for dropped objects) on the clone
DROP TABLE BUS.BUS_MASTER_CLONE;
SHOW TABLES HISTORY LIKE 'BUS_MASTER_CLONE' IN SCHEMA BUS;
UNDROP TABLE BUS.BUS_MASTER_CLONE;
SELECT COUNT(*) AS CLONE_ROWS_AFTER_UNDROP FROM BUS.BUS_MASTER_CLONE;
