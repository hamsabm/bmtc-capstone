# Test results

Executed 2026-11-08 against Snowflake account `OTSODYW-YJ16532` (AWS ap-southeast-7, role ACCOUNTADMIN)
after a **complete rebuild from zero** (`scripts/run_sql.py`). The raw output of every statement is in `logs/`.

## SQL scripts (all executed)

| Script | Result |
|---|---|
| 01_database_setup | 13 ok |
| 02_tables | 17 ok |
| 03_data_loading | 52 ok |
| 03b_snowpipe | 13 ok. Pipe loaded 25 new complaints (460 → 485) |
| 04_advanced_sql | 36 ok. COMMIT changed 5 bus statuses with audit rows; ROLLBACK restored 141 deleted tickets |
| 05_json_variant | 13 ok |
| 06_views | 19 ok. Materialized view created and queried |
| 07_time_travel_clone | 23 ok. Fare checksum 2205 → x10 error → recovered 2205 (`RECOVERED`); clone + DROP/UNDROP |
| 08_streams_tasks | 37 ok. Reconciliation 0 → 2 after change → task SUCCEEDED → 0; clean-up cycle → 0 |
| 09_security | 111 ok, 1 skipped (idempotent detach of a policy not yet attached). All 4 denial tests returned errors |
| 10_python_udf | 18 ok. UDFs return GOOD/POOR/UNKNOWN as expected; Snowpark procedure scored 10 depots |
| 11_performance | 25 ok. Resource monitor attached; pruning stats captured |
| 12_data_sharing | 11 ok. Share created with the secure view |
| powerbi/dashboard_queries | 21 ok |

## Data loading and quality (03)

| Check | Before fix | After fix |
|---|---|---|
| Duplicate TRIP_ID rows | 5 | 0 |
| Negative PASSENGER_COUNT | 3 | 0 |
| Duplicate TICKET_ID rows | 10 | 0 |
| Orphan tickets | 3 | 0 |
| Pass STATUS case/whitespace | 8 | 0 |
| Missing pass VALID_TO | 4 | 0 |
| Missing fuel QUANTITY | 4 | 0 (imputed from cost / unit price) |
| Non-numeric fuel QUANTITY (rejected by COPY, logged in `STAGING.LOAD_REJECTS`) | 1 | excluded |
| Negative maintenance PARTS_COST | 3 | 0 |
| Trip PASSENGER_COUNT ≠ tickets issued | – | 0 |
| Trips/complaints referencing unknown bus/route/trip | – | 0 |
| Missing pass e-mail (optional field, reported only) | 234 | 234 |

Row counts: depots 10, buses 120, employees 300, routes 40, trips 3,945, tickets 120,718, fuel 383,
maintenance 713, passes 1,500, complaints 485.

## Final validation (`scripts/validate.py`): 38/38 PASS

Covers: warehouse (XSMALL, 60 s, auto-resume, resource monitor), database, 5 schemas, 10 tables with minimum
row counts, VARIANT column, permanent + transient tables, 14 standard views, 4 secure views, materialized view,
stream (not stale), task (started, 2 succeeded / 0 failed), summary reconciliation, Snowpipe, Python UDFs and
procedures, 4 roles, 4 users, masking + row access policies, share, no duplicate keys, viewer least privilege,
**password absent from every project file except `.env`**, and `.env` git-ignored.

## Application

| Test | Result |
|---|---|
| Python syntax check, all project files | PASS |
| `tests/test_app.py`: every page runs headless with live data, no exception / no `st.error` | 9/9 PASS (40 charts rendered) |
| `tests/test_interactions.py`: search, filters, SQL-injection text, empty results, all 11 advanced queries, 3 write forms verified in Snowflake then cleaned up | 24/24 PASS |
| `streamlit run app.py` server start, `/_stcore/health` = ok, pages HTTP 200 | PASS |

### Finalization re-test (after navigation / error-handling polish)

| Test | Result |
|---|---|
| `scripts/validate.py` | 38/38 PASS |
| `tests/test_app.py` | 9/9 PASS |
| `tests/test_navigation_errors.py`: Home + all 8 pages through `st.navigation`; unreachable Snowflake gives one clean message, no traceback, no KPI values | 10/10 PASS |
| `tests/test_interactions.py` (forms write to Snowflake, verified, cleaned up) | 24/24 PASS |
| Local site `http://localhost:8501`: health `ok`; `/`, `/dashboard`, `/bus_management`, `/routes_trips`, `/ticket_analytics`, `/fuel_maintenance`, `/passengers_complaints`, `/advanced_analytics`, `/data_management` | HTTP 200 |
| Key-pair connection config (offline, throwaway key): builds `SNOWFLAKE_JWT` config, no password used | PASS |
| Key-pair login against Snowflake as `BMTC_STREAMLIT_APP` | see deployment check below |

### Deployment check: limited application identity

`sql/13_app_service_user.sql` (23 ok) and `scripts/setup_app_user.py` were run. The service user `BMTC_STREAMLIT_APP`
(role `BMTC_APP`, `TYPE = SERVICE`, RSA key-pair, no password) was created.

| Test (run as BMTC_STREAMLIT_APP, password blanked) | Result |
|---|---|
| `tests/test_app_user.py`: key-pair auth; cannot `USE ROLE ACCOUNTADMIN`/`SYSADMIN`; only `BMTC_APP` granted; CREATE USER, GRANT, DROP TABLE, DELETE tickets, ALTER WAREHOUSE and ACCOUNT_USAGE all denied; PII masked; salaries hidden; reads KPIs, all depots, pipe/stream status, UDF | 18/18 PASS |
| `tests/test_app.py` | 9/9 PASS |
| `tests/test_navigation_errors.py` | 10/10 PASS |
| `tests/test_interactions.py`: the three forms write as BMTC_APP; verification and clean-up use the owner account from `.env` | 24/24 PASS |
| `.gitignore` checked with `git check-ignore`: `.env`, `secrets/*`, `*.p8`/`*.pem`/`*.key`, `*credentials*`, `venv/` ignored | PASS |
| Password / private-key material in any committable file (74 files) | none |

Fix made during this check: Data Management → Security now explains that policy metadata is admin-only. Before,
it showed an empty table for the limited role.

## Security role tests (09, secondary roles disabled)

| Role | Result |
|---|---|
| BMTC_VIEWER | Reads KPI view + secure pass view. PASS_DATA denied, revoked TICKET_DATA denied, secure-view DDL hidden |
| BMTC_ANALYST | Name/phone/e-mail masked (`V*****`, `XXXXXX5846`, `*****@...`), salary NULL, DELETE denied, all 10 depots visible |
| BMTC_MANAGER | Phone visible, salary NULL, row access limits view to depots 1–2, payroll aggregates visible via secure view |
| BMTC_ADMIN | Unmasked, all depots |

## Not tested / not possible here

- Power BI dashboard: no `.pbix` created (manual GUI step).
- Visual inspection of charts in a browser: charts were verified to render via Streamlit's test runner and the
  server returned HTTP 200. No screenshot was taken.
- Share consumption: no second Snowflake account is available.
- Public deployment: not performed (requires your GitHub / Streamlit Cloud login). The app is local only.
