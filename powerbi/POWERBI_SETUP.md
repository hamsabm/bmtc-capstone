# Power BI setup

The Snowflake side is ready and tested (`logs/dashboard_queries.log`). The `.pbix` file has **not** been
created. Build it in Power BI Desktop with the steps below.

## 1. Connect

Power BI Desktop → **Get data → Snowflake**

| Field | Value |
|---|---|
| Server | `OTSODYW-YJ16532.snowflakecomputing.com` |
| Warehouse | `BMTC_WH` |
| Advanced → Role | `BMTC_VIEWER` (least privilege) or `ACCOUNTADMIN` |
| Database | `BMTC_DW` |
| Authentication | Snowflake user name + password |
| Mode | **Import** (dataset is small; avoids keeping the warehouse running) |

To use the BI service account, set its password first (see `MANUAL_STEPS.md`). If you use your own login, note
that `BMTC_VIEWER` can read only the curated views below, which is intended.

## 2. Load these views

| View | Grain | Use |
|---|---|---|
| `TRIP.V_DASHBOARD_KPIS` | 1 row | KPI cards |
| `TRIP.V_PBI_DIM_DATE` | day | Date dimension (mark as date table) |
| `TRIP.V_PBI_ROUTE_DAY_FACT` | route × day | Revenue, ridership, punctuality trends |
| `TRIP.V_ROUTE_PERFORMANCE` | route | Top/bottom routes, ranking |
| `TRIP.V_FUEL_EFFICIENCY_CLASSIFIED` | fuel event | Fuel cost, efficiency, Python-UDF class |
| `TRIP.V_MAINTENANCE_DETAILS` | job | Maintenance cost / frequency |
| `BUS.V_BUS_SUMMARY` | bus | Fleet comparison |
| `PASSENGER.V_COMPLAINT_ANALYTICS` | complaint | Category / priority / channel (from JSON) |
| `PASSENGER.V_PASS_SUMMARY` | month × pass type | Pass sales |

Relationships: `V_PBI_DIM_DATE[DATE_KEY]` 1→* `V_PBI_ROUTE_DAY_FACT[DATE_KEY]`;
`V_ROUTE_PERFORMANCE[ROUTE_ID]` 1→* `V_PBI_ROUTE_DAY_FACT[ROUTE_ID]`.

## 3. Suggested report page

| Visual | Field(s) | Concept |
|---|---|---|
| Cards | TOTAL_TRIPS, TICKET_REVENUE, ON_TIME_PCT, OPEN_COMPLAINTS, ACTIVE_PASSES | KPIs |
| Line | YEAR_MONTH × sum REVENUE / PASSENGERS | Trend / time analysis |
| Column | WEEKDAY × avg daily PASSENGERS | Time analysis |
| Bar | DEPOT_NAME × REVENUE, ON_TIME_PCT | Comparison |
| Donut / bar | ROUTE_CATEGORY × REVENUE | Category analysis |
| Stacked bar | CATEGORY × COMPLAINTS by PRIORITY | Category analysis (JSON data) |
| Bar (Top N filter) | ROUTE_CODE × REVENUE, Top 10 and Bottom 10 | Top/bottom performers |
| Table | REGISTRATION_NO, MAINTENANCE_COST, KM_PER_UNIT (top 10 cost) | Top/bottom |
| Slicers | DEPOT_NAME, ROUTE_CATEGORY, YEAR_MONTH | Filtering |

Example DAX measures:

```DAX
Revenue = SUM(V_PBI_ROUTE_DAY_FACT[REVENUE])
On-time % = DIVIDE(SUM(V_PBI_ROUTE_DAY_FACT[ON_TIME_TRIPS]), SUM(V_PBI_ROUTE_DAY_FACT[TRIPS]))
Revenue per km = DIVIDE([Revenue], SUM(V_PBI_ROUTE_DAY_FACT[KM]))
```

Every query behind these visuals is in `dashboard_queries.sql`. Their verified outputs are in
`logs/dashboard_queries.log` and can be used to cross-check the dashboard numbers. Example values:
City Ordinary Rs 5.41 L revenue across 66,264 passengers; peak trips average 13.7 min delay versus 3.1 min off-peak.
