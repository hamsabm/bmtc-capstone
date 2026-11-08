-- =====================================================================
-- 03b_snowpipe.sql | Continuous ingestion of new passenger complaints
-- New complaint files (from the helpline / mobile app export) land in
-- @STAGING.BMTC_INTERNAL_STAGE/feed/ and a PIPE loads them into
-- PASSENGER.COMPLAINTS_JSON.
-- Internal stages do not emit cloud event notifications, so AUTO_INGEST is
-- not available here; the pipe is triggered with ALTER PIPE ... REFRESH
-- (or the Snowpipe REST insertFiles API). With an external S3/Azure/GCS
-- stage, AUTO_INGEST = TRUE + event notifications make it fully automatic.
-- Run after 02/03 (02 recreates the target table).
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

CREATE OR REPLACE PIPE STAGING.PIPE_COMPLAINTS_FEED
  COMMENT = 'Snowpipe: new complaint JSON files -> PASSENGER.COMPLAINTS_JSON'
AS
COPY INTO PASSENGER.COMPLAINTS_JSON (COMPLAINT_ID, SUBMITTED_AT, PAYLOAD, SOURCE_FILE)
FROM (SELECT $1:complaint_id::VARCHAR, $1:submitted_at::TIMESTAMP_NTZ, $1, METADATA$FILENAME
      FROM @STAGING.BMTC_INTERNAL_STAGE/feed/)
FILE_FORMAT = (FORMAT_NAME = 'STAGING.FF_JSON');

SHOW PIPES IN SCHEMA STAGING;
SELECT COUNT(*) AS COMPLAINTS_BEFORE_FEED FROM PASSENGER.COMPLAINTS_JSON;

-- A new file arrives
PUT 'file://{{DATA_DIR}}/incremental/complaints_feed_001.json' @STAGING.BMTC_INTERNAL_STAGE/feed/ AUTO_COMPRESS = TRUE OVERWRITE = TRUE;

-- Notify the pipe (queues staged files not yet loaded by this pipe)
ALTER PIPE STAGING.PIPE_COMPLAINTS_FEED REFRESH;

-- Snowpipe is asynchronous (serverless); wait, then verify
SELECT SYSTEM$WAIT(45, 'SECONDS');
SELECT SYSTEM$PIPE_STATUS('STAGING.PIPE_COMPLAINTS_FEED') AS PIPE_STATUS;
SELECT SYSTEM$WAIT(30, 'SECONDS');
SELECT COUNT(*) AS COMPLAINTS_AFTER_FEED,
       COUNT_IF(SOURCE_FILE LIKE 'feed/%') AS LOADED_BY_SNOWPIPE
FROM PASSENGER.COMPLAINTS_JSON;
SELECT FILE_NAME, STATUS, ROW_COUNT, PIPE_NAME, LAST_LOAD_TIME
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => 'PASSENGER.COMPLAINTS_JSON',
                                           START_TIME => DATEADD(HOUR, -2, CURRENT_TIMESTAMP())))
WHERE PIPE_NAME IS NOT NULL;
