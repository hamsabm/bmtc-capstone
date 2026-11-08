-- =====================================================================
-- 05_json_variant.sql | Semi-structured complaint documents (VARIANT)
-- PASSENGER.COMPLAINTS_JSON.PAYLOAD holds nested JSON: passenger{}, service{},
-- location{geo{}}, tags[], resolution{assigned_to{}} ...
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE BMTC_WH;
USE DATABASE BMTC_DW;

-- 1. Raw document and data types inside the VARIANT
SELECT COMPLAINT_ID, PAYLOAD FROM PASSENGER.COMPLAINTS_JSON ORDER BY COMPLAINT_ID LIMIT 2;
SELECT TYPEOF(PAYLOAD) AS DOC_TYPE, TYPEOF(PAYLOAD:tags) AS TAGS_TYPE, TYPEOF(PAYLOAD:service.trip_id) AS TRIP_ID_TYPE,
       OBJECT_KEYS(PAYLOAD) AS TOP_LEVEL_KEYS
FROM PASSENGER.COMPLAINTS_JSON LIMIT 1;

-- 2. Path extraction incl. nested objects (dot and bracket notation) with casting
SELECT COMPLAINT_ID,
       PAYLOAD:category::VARCHAR                              AS CATEGORY,
       PAYLOAD:sub_category::VARCHAR                          AS SUB_CATEGORY,
       PAYLOAD:priority::VARCHAR                              AS PRIORITY,
       PAYLOAD:channel::VARCHAR                               AS CHANNEL,
       PAYLOAD:service.route_code::VARCHAR                    AS ROUTE_CODE,
       PAYLOAD['service']['bus_id']::NUMBER                   AS BUS_ID,
       PAYLOAD:location.geo.lat::FLOAT                        AS LAT,
       PAYLOAD:location.geo.lon::FLOAT                        AS LON,
       PAYLOAD:resolution.status::VARCHAR                     AS RESOLUTION_STATUS,
       PAYLOAD:resolution.assigned_to.employee_id::NUMBER     AS ASSIGNED_SUPERVISOR,
       PAYLOAD:resolution.resolution_days::NUMBER             AS RESOLUTION_DAYS,
       PAYLOAD:passenger.pass_id::NUMBER                      AS PASS_ID,
       ARRAY_SIZE(PAYLOAD:tags)                               AS TAG_COUNT
FROM PASSENGER.COMPLAINTS_JSON ORDER BY SUBMITTED_AT DESC LIMIT 20;

-- 3. Filtering on JSON attributes: unresolved high-priority safety complaints
SELECT COMPLAINT_ID, SUBMITTED_AT, PAYLOAD:description::VARCHAR AS DESCRIPTION, PAYLOAD:resolution.status::VARCHAR AS STATUS
FROM PASSENGER.COMPLAINTS_JSON
WHERE PAYLOAD:category::VARCHAR = 'Safety'
  AND PAYLOAD:priority::VARCHAR = 'High'
  AND PAYLOAD:resolution.status::VARCHAR IN ('Open', 'In Progress');

-- 4. Aggregation: category x priority with resolution KPIs
SELECT PAYLOAD:category::VARCHAR AS CATEGORY,
       COUNT(*) AS COMPLAINTS,
       COUNT_IF(PAYLOAD:priority::VARCHAR = 'High') AS HIGH_PRIORITY,
       ROUND(100 * COUNT_IF(PAYLOAD:resolution.status::VARCHAR = 'Resolved') / COUNT(*), 1) AS RESOLVED_PCT,
       ROUND(AVG(PAYLOAD:resolution.resolution_days::NUMBER), 1) AS AVG_RESOLUTION_DAYS,
       ROUND(AVG(PAYLOAD:resolution.satisfaction_rating::NUMBER), 2) AS AVG_SATISFACTION
FROM PASSENGER.COMPLAINTS_JSON
GROUP BY CATEGORY ORDER BY COMPLAINTS DESC;

-- 5. LATERAL FLATTEN of the tags array
SELECT t.VALUE::VARCHAR AS TAG, COUNT(*) AS COMPLAINTS
FROM PASSENGER.COMPLAINTS_JSON c, LATERAL FLATTEN(INPUT => c.PAYLOAD:tags) t
GROUP BY TAG ORDER BY COMPLAINTS DESC;

-- 6. JSON joined with relational tables: complaints per 1,000 passengers by route
SELECT r.ROUTE_CODE, r.ROUTE_CATEGORY, COUNT(c.COMPLAINT_ID) AS COMPLAINTS, p.PASSENGERS,
       ROUND(1000 * COUNT(c.COMPLAINT_ID) / NULLIF(p.PASSENGERS, 0), 2) AS COMPLAINTS_PER_1000_PAX
FROM TRIP.ROUTE_MASTER r
JOIN (SELECT ROUTE_ID, SUM(PASSENGER_COUNT) AS PASSENGERS FROM TRIP.TRIP_DATA GROUP BY ROUTE_ID) p ON p.ROUTE_ID = r.ROUTE_ID
LEFT JOIN PASSENGER.COMPLAINTS_JSON c ON c.PAYLOAD:service.route_id::NUMBER = r.ROUTE_ID
GROUP BY r.ROUTE_CODE, r.ROUTE_CATEGORY, p.PASSENGERS
ORDER BY COMPLAINTS_PER_1000_PAX DESC LIMIT 10;

-- 7. Delay complaints vs actual recorded trip delay (JSON -> TRIP_DATA join)
SELECT PAYLOAD:category::VARCHAR AS CATEGORY, COUNT(*) AS COMPLAINTS, ROUND(AVG(t.DELAY_MINUTES), 1) AS AVG_ACTUAL_DELAY,
       COUNT_IF(t.TRIP_STATUS = 'CANCELLED') AS ON_CANCELLED_TRIPS
FROM PASSENGER.COMPLAINTS_JSON c
JOIN TRIP.TRIP_DATA t ON t.TRIP_ID = c.PAYLOAD:service.trip_id::NUMBER
GROUP BY CATEGORY ORDER BY AVG_ACTUAL_DELAY DESC NULLS LAST;

-- 8. Monthly complaint trend by channel (time analysis on JSON)
SELECT DATE_TRUNC('MONTH', SUBMITTED_AT) AS MONTH, PAYLOAD:channel::VARCHAR AS CHANNEL, COUNT(*) AS COMPLAINTS
FROM PASSENGER.COMPLAINTS_JSON GROUP BY MONTH, CHANNEL ORDER BY MONTH, CHANNEL;

-- 9. Building JSON in SQL (OBJECT_CONSTRUCT) - a per-route complaint summary document
SELECT OBJECT_CONSTRUCT('route_code', PAYLOAD:service.route_code::VARCHAR,
                        'complaints', COUNT(*),
                        'categories', ARRAY_AGG(DISTINCT PAYLOAD:category::VARCHAR)) AS ROUTE_COMPLAINT_DOC
FROM PASSENGER.COMPLAINTS_JSON GROUP BY PAYLOAD:service.route_code::VARCHAR ORDER BY COUNT(*) DESC LIMIT 5;
