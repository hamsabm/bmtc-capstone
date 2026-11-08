-- =====================================================================
-- 11_performance.sql | Warehouse sizing, cost controls, micro-partitions,
-- pruning, clustering evaluation and query-performance evidence.
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

-- ---------------------------------------------------------------- Warehouse & cost controls
ALTER WAREHOUSE BMTC_WH SET
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 600          -- runaway query protection
  STATEMENT_QUEUED_TIMEOUT_IN_SECONDS = 300;
SHOW WAREHOUSES LIKE 'BMTC_WH';

-- Credit guard for the trial: notify at 75%, suspend the warehouse at 100% of 5 credits/month
CREATE OR REPLACE RESOURCE MONITOR BMTC_RM WITH
  CREDIT_QUOTA = 5
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND
           ON 110 PERCENT DO SUSPEND_IMMEDIATE;                                     -- @optional
ALTER WAREHOUSE BMTC_WH SET RESOURCE_MONITOR = BMTC_RM;                             -- @optional
SHOW RESOURCE MONITORS LIKE 'BMTC_RM';                                              -- @optional

-- Scaling (documented, not enabled to protect trial credits):
--   Scale UP   (bigger size) for heavy single queries:  ALTER WAREHOUSE BMTC_WH SET WAREHOUSE_SIZE = 'SMALL';
--   Scale OUT  (multi-cluster, Enterprise) for many concurrent dashboard users:
--              ALTER WAREHOUSE BMTC_WH SET MIN_CLUSTER_COUNT = 1 MAX_CLUSTER_COUNT = 3 SCALING_POLICY = 'ECONOMY';

-- ---------------------------------------------------------------- Micro-partitions
SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT, BYTES, ROUND(BYTES / 1024 / 1024, 2) AS MB, RETENTION_TIME, IS_TRANSIENT
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('BUS', 'TRIP', 'PASSENGER') AND TABLE_TYPE = 'BASE TABLE'
ORDER BY BYTES DESC;

-- Clustering depth of the largest table on its most common filter column
SELECT SYSTEM$CLUSTERING_INFORMATION('TRIP.TICKET_DATA', '(TICKET_DATE)') AS TICKET_DATE_CLUSTERING;
SELECT SYSTEM$CLUSTERING_INFORMATION('TRIP.TICKET_DATA', '(ROUTE_ID)')    AS ROUTE_CLUSTERING;

-- ---------------------------------------------------------------- Query performance evidence
ALTER SESSION SET USE_CACHED_RESULT = FALSE;     -- measure real execution, not the result cache

-- Filtered query: pruning statistics from the operator profile
SELECT ROUTE_ID, COUNT(*) AS TICKETS, SUM(FARE) AS REVENUE
FROM TRIP.TICKET_DATA WHERE TICKET_DATE BETWEEN '2026-10-01' AND '2026-10-31' GROUP BY ROUTE_ID;
SET q_filtered = LAST_QUERY_ID();
SELECT OPERATOR_TYPE, OPERATOR_STATISTICS:pruning:partitions_scanned::NUMBER AS PARTITIONS_SCANNED,
       OPERATOR_STATISTICS:pruning:partitions_total::NUMBER AS PARTITIONS_TOTAL,
       EXECUTION_TIME_BREAKDOWN:overall_percentage::FLOAT AS PCT_OF_QUERY
FROM TABLE(GET_QUERY_OPERATOR_STATS($q_filtered)) WHERE OPERATOR_TYPE = 'TableScan';

-- Same daily revenue question: base table aggregation vs materialized view
SELECT TICKET_DATE, SUM(FARE) FROM TRIP.TICKET_DATA GROUP BY TICKET_DATE ORDER BY TICKET_DATE;
SET q_base = LAST_QUERY_ID();
SELECT TICKET_DATE, SUM(REVENUE) FROM TRIP.MV_DAILY_ROUTE_REVENUE GROUP BY TICKET_DATE ORDER BY TICKET_DATE;
SET q_mv = LAST_QUERY_ID();

ALTER SESSION SET USE_CACHED_RESULT = TRUE;
-- Result cache: identical repeated query is served without warehouse compute
SELECT COUNT(*) FROM TRIP.TICKET_DATA WHERE PAYMENT_MODE = 'UPI';
SELECT COUNT(*) FROM TRIP.TICKET_DATA WHERE PAYMENT_MODE = 'UPI';
SET q_cached = LAST_QUERY_ID();

SELECT QUERY_ID, LEFT(QUERY_TEXT, 70) AS QUERY, TOTAL_ELAPSED_TIME AS ELAPSED_MS, BYTES_SCANNED, ROWS_PRODUCED
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 50))
WHERE QUERY_ID IN ($q_filtered, $q_base, $q_mv, $q_cached)
ORDER BY START_TIME;

-- EXPLAIN plan for the dashboard route query
EXPLAIN SELECT ROUTE_CODE, REVENUE FROM TRIP.V_ROUTE_PERFORMANCE ORDER BY REVENUE DESC LIMIT 10;

-- ---------------------------------------------------------------- Clustering decision
-- TICKET_DATA (~120k rows, a few MB) fits in very few micro-partitions, so a clustering key
-- would add automatic-clustering cost without measurable benefit. At production scale
-- (hundreds of millions of tickets/year) the recommended key is:
--   ALTER TABLE TRIP.TICKET_DATA CLUSTER BY (TICKET_DATE, ROUTE_ID);
-- because almost every analytical query filters on a date range and groups by route.
