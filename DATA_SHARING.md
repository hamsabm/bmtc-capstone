# Data sharing

## Implemented (provider side, executed in `sql/12_data_sharing.sql`)

| Object | Purpose |
|---|---|
| `TRIP.SV_SHARE_ROUTE_DAILY` (secure view) | Daily route ridership, trips and delay. No personal data. |
| Share `BMTC_ROUTE_PERFORMANCE_SHARE` | Grants USAGE on `BMTC_DW` / `TRIP` and SELECT on the secure view. `secure_objects_only = true`. |

Verified with `SHOW SHARES` and `DESC SHARE` (`logs/12_data_sharing.log`).

**Limitation:** no consumer was added because a share is consumed by another Snowflake account in the same
region, and this project has only one trial account. With a second account:

```sql
ALTER SHARE BMTC_ROUTE_PERFORMANCE_SHARE ADD ACCOUNTS = <ORG>.<CONSUMER_ACCOUNT>;
-- consumer:
CREATE DATABASE BMTC_SHARED FROM SHARE OTSODYW.YJ16532.BMTC_ROUTE_PERFORMANCE_SHARE;
```

Nothing is copied. The consumer queries live BMTC data with its own warehouse, and revoking the grant
removes access immediately.

## Use in this project

- **Secure Data Sharing:** route ridership and punctuality shared with a metro operator or a city transport
  planning body for feeder-route planning. Only aggregated, non-personal data leaves BMTC.
- **Data Exchange (private listing):** a controlled group, such as the transport department, the smart-city SPV and
  partner operators, subscribes to curated BMTC datasets through a listing with usage terms and a
  data dictionary.
- **Marketplace:** BMTC can consume weather, holiday-calendar, fuel-price or geospatial (POI / road
  network) datasets to explain delay and ridership patterns. BMTC could also publish an open-data listing
  of route performance. In this account, `Data Products > Marketplace` in Snowsight lists the free datasets available.
