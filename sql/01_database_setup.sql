-- =====================================================================
-- 01_database_setup.sql  |  BMTC Data Warehouse - Snowflake environment
-- Safe to re-run (IF NOT EXISTS everywhere).
-- =====================================================================
USE ROLE ACCOUNTADMIN;

-- Virtual warehouse: smallest size, suspends after 60 s idle, wakes on demand.
CREATE WAREHOUSE IF NOT EXISTS BMTC_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'BMTC capstone compute - XSMALL, auto-suspend 60s';

CREATE DATABASE IF NOT EXISTS BMTC_DW
  DATA_RETENTION_TIME_IN_DAYS = 1
  COMMENT = 'BMTC Data Warehouse';

ALTER DATABASE BMTC_DW SET COMMENT = 'BMTC Data Warehouse';

USE DATABASE BMTC_DW;
USE WAREHOUSE BMTC_WH;

-- Functional-area schemas
CREATE SCHEMA IF NOT EXISTS BMTC_DW.BUS       COMMENT = 'Fleet, depot and workforce master data';
CREATE SCHEMA IF NOT EXISTS BMTC_DW.TRIP      COMMENT = 'Operations: routes, trips, ticketing, fuel, maintenance';
CREATE SCHEMA IF NOT EXISTS BMTC_DW.PASSENGER COMMENT = 'Passenger passes and complaint documents (JSON)';
-- Supporting schemas
CREATE SCHEMA IF NOT EXISTS BMTC_DW.STAGING    COMMENT = 'Landing zone: stage, file formats, transient load tables, pipe';
CREATE SCHEMA IF NOT EXISTS BMTC_DW.GOVERNANCE COMMENT = 'Masking and row access policies, access mapping';

-- Verification
SHOW WAREHOUSES LIKE 'BMTC_WH';
SHOW SCHEMAS IN DATABASE BMTC_DW;
SELECT CURRENT_ACCOUNT() AS ACCOUNT, CURRENT_ROLE() AS ROLE, CURRENT_WAREHOUSE() AS WAREHOUSE,
       CURRENT_DATABASE() AS DATABASE_NAME;
