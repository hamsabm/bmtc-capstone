# Power BI Setup & Integration Guide

The Snowflake data warehouse is fully populated, validated, and verified with all 8 curated BI views live.

The repository includes a ready-to-use **Power BI Project (`powerbi/BMTC_Dashboard.pbip`)** configured with Tabular Model Definition Language (TMDL) semantic models, DAX measures, and curated visual reports.

---

## Method 1: Instant Launch via Power BI Project (Recommended)

1. Open **Microsoft Power BI Desktop** (installed at `C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe`).
2. Double-click or open:
   ```
   powerbi/BMTC_Dashboard.pbip
   ```
3. Power BI Desktop will automatically load:
   - **Report**: `BMTC_Dashboard.Report` (Overview & Fleet pages with KPIs, bar charts, trend lines, and slicers)
   - **Semantic Model**: `BMTC_Dashboard.SemanticModel` (8 dimension and fact tables, DAX measures, and relationships)
4. When prompted for credentials:
   - Select **Snowflake** or **Database Account**
   - Enter your Snowflake username and password
   - Ensure the server name is `OTSODYW-YJ16532.snowflakecomputing.com` and warehouse is `BMTC_WH`
5. Click **Refresh** to pull the latest live data from Snowflake.
6. To create a standalone `.pbix` file, click **File → Save As → Power BI file (*.pbix)** and save it as `BMTC_Dashboard.pbix`.

---

## Method 2: Manual Import / Custom Report

If you prefer building a custom report from scratch in Power BI Desktop:

### 1. Connection Parameters
Power BI Desktop → **Get data → Snowflake**

| Field | Value |
|---|---|
| **Server** | `OTSODYW-YJ16532.snowflakecomputing.com` |
| **Warehouse** | `BMTC_WH` |
| **Database** | `BMTC_DW` |
| **Advanced → Role** | `BMTC_VIEWER` (least privilege) or `ACCOUNTADMIN` |
| **Mode** | **Import** (recommended for speed and to avoid warehouse uptime) or **DirectQuery** |

### 2. Curated Views to Load

| View | Grain | Verified Row Count | Purpose |
|---|---|---|---|
| `TRIP.V_DASHBOARD_KPIS` | 1 row | 1 | Executive headline KPI cards |
| `TRIP.V_PBI_DIM_DATE` | Day | 365 | Date dimension (mark as date table) |
| `TRIP.V_PBI_ROUTE_DAY_FACT` | Route × Day | 3,349 | Revenue, ridership, and punctuality trends |
| `TRIP.V_ROUTE_PERFORMANCE` | Route | 40 | Top/bottom route rankings |
| `TRIP.V_FUEL_EFFICIENCY_CLASSIFIED` | Fuel event | 383 | Fuel cost, efficiency, UDF classification |
| `TRIP.V_MAINTENANCE_DETAILS` | Job | 713 | Maintenance cost & frequency |
| `BUS.V_BUS_SUMMARY` | Bus | 120 | Fleet composition & status |
| `PASSENGER.V_COMPLAINT_ANALYTICS` | Complaint | 485 | Category, priority, channel analytics |

### 3. Relationships
- `V_PBI_DIM_DATE[DATE_KEY]` 1 → * `V_PBI_ROUTE_DAY_FACT[DATE_KEY]`
- `V_ROUTE_PERFORMANCE[ROUTE_ID]` 1 → * `V_PBI_ROUTE_DAY_FACT[ROUTE_ID]`

### 4. Key DAX Measures

```DAX
Total Revenue = SUM(V_PBI_ROUTE_DAY_FACT[REVENUE])

On-time % = DIVIDE(SUM(V_PBI_ROUTE_DAY_FACT[ON_TIME_TRIPS]), SUM(V_PBI_ROUTE_DAY_FACT[TRIPS]))

Revenue per KM = DIVIDE([Total Revenue], SUM(V_PBI_ROUTE_DAY_FACT[KM]))

Avg Delay Minutes = AVERAGE(V_PBI_ROUTE_DAY_FACT[AVG_DELAY_MINUTES])
```

All SQL queries used by these views are documented in `powerbi/dashboard_queries.sql` and verified in `logs/dashboard_queries.log`.
