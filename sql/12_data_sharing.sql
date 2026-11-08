-- =====================================================================
-- 12_data_sharing.sql | Secure Data Sharing (provider side)
-- Shares aggregated, non-personal route performance with a partner account
-- (e.g. Bangalore Metro / Directorate of Urban Land Transport). Only secure
-- views can be shared. Adding a consumer requires a real consumer account
-- locator - see DATA_SHARING.md.
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

CREATE OR REPLACE SECURE VIEW TRIP.SV_SHARE_ROUTE_DAILY
COMMENT = 'Shareable: daily route ridership, revenue and punctuality - no personal data' AS
SELECT r.ROUTE_CODE, r.ROUTE_CATEGORY, r.SOURCE_STOP, r.DESTINATION_STOP, t.TRIP_DATE,
       COUNT(*) AS TRIPS, SUM(t.PASSENGER_COUNT) AS PASSENGERS, ROUND(AVG(t.DELAY_MINUTES), 1) AS AVG_DELAY_MIN
FROM TRIP.TRIP_DATA t JOIN TRIP.ROUTE_MASTER r ON r.ROUTE_ID = t.ROUTE_ID
GROUP BY r.ROUTE_CODE, r.ROUTE_CATEGORY, r.SOURCE_STOP, r.DESTINATION_STOP, t.TRIP_DATE;

CREATE SHARE IF NOT EXISTS BMTC_ROUTE_PERFORMANCE_SHARE
  COMMENT = 'BMTC (synthetic) route performance for transport planning partners';      -- @optional
GRANT USAGE ON DATABASE BMTC_DW TO SHARE BMTC_ROUTE_PERFORMANCE_SHARE;                 -- @optional
GRANT USAGE ON SCHEMA BMTC_DW.TRIP TO SHARE BMTC_ROUTE_PERFORMANCE_SHARE;              -- @optional
GRANT SELECT ON VIEW BMTC_DW.TRIP.SV_SHARE_ROUTE_DAILY TO SHARE BMTC_ROUTE_PERFORMANCE_SHARE; -- @optional
SHOW SHARES LIKE 'BMTC_ROUTE_PERFORMANCE_SHARE';                                        -- @optional
DESC SHARE BMTC_ROUTE_PERFORMANCE_SHARE;                                                -- @optional

-- Consumer side test: simulate what the consumer will see
SELECT ROUTE_CODE, SUM(PASSENGERS) AS PASSENGERS FROM TRIP.SV_SHARE_ROUTE_DAILY
GROUP BY ROUTE_CODE ORDER BY PASSENGERS DESC LIMIT 5;

-- To actually deliver the share (needs a second Snowflake account in the same region):
--   ALTER SHARE BMTC_ROUTE_PERFORMANCE_SHARE ADD ACCOUNTS = <ORG>.<CONSUMER_ACCOUNT>;
-- Consumer:  CREATE DATABASE BMTC_SHARED FROM SHARE <PROVIDER_ORG>.<PROVIDER_ACCOUNT>.BMTC_ROUTE_PERFORMANCE_SHARE;
