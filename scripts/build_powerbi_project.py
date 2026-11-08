r"""Generate the Power BI Project (PBIP) for the BMTC dashboard from live Snowflake metadata.

Output: powerbi/BMTC_Dashboard.pbip  (+ .SemanticModel and .Report folders, text-based)
Open the .pbip in Power BI Desktop, sign in to Snowflake when prompted, Refresh, then File > Save As .pbix.
No credentials are written to any file; Power BI stores them in its own credential store.
Run: venv\Scripts\python.exe scripts\build_powerbi_project.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.snowflake_connection import connection, run_query  # noqa: E402

NAME = "BMTC_Dashboard"
OUT = ROOT / "powerbi"
SM = OUT / f"{NAME}.SemanticModel"
RP = OUT / f"{NAME}.Report"
SERVER = f"{os.environ['SNOWFLAKE_ACCOUNT']}.snowflakecomputing.com"
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "BMTC_WH")
NS = uuid.UUID("6f1c2a4e-1b0d-4c55-9a77-0b6d1c0f5a10")

# model table -> (schema, view)
TABLES = {
    "KPI": ("TRIP", "V_DASHBOARD_KPIS"),
    "DimDate": ("TRIP", "V_PBI_DIM_DATE"),
    "RouteDay": ("TRIP", "V_PBI_ROUTE_DAY_FACT"),
    "Routes": ("TRIP", "V_ROUTE_PERFORMANCE"),
    "Fuel": ("TRIP", "V_FUEL_EFFICIENCY_CLASSIFIED"),
    "Maintenance": ("TRIP", "V_MAINTENANCE_DETAILS"),
    "Complaints": ("PASSENGER", "V_COMPLAINT_ANALYTICS"),
    "Buses": ("BUS", "V_BUS_SUMMARY"),
}
MEASURES = {
    "RouteDay": [("Total Revenue", "SUM(RouteDay[REVENUE])", "#,0"),
                 ("Total Passengers", "SUM(RouteDay[PASSENGERS])", "#,0"),
                 ("Total Trips", "SUM(RouteDay[TRIPS])", "#,0"),
                 ("On-time %", "DIVIDE(SUM(RouteDay[ON_TIME_TRIPS]), SUM(RouteDay[TRIPS]))", "0.0%"),
                 ("Revenue per km", "DIVIDE(SUM(RouteDay[REVENUE]), SUM(RouteDay[KM]))", "#,0.00")],
    "Complaints": [("Complaint Count", "COUNTROWS(Complaints)", "#,0"),
                   ("Open Complaints", 'CALCULATE(COUNTROWS(Complaints), Complaints[RESOLUTION_STATUS] IN {"Open", "In Progress"})', "#,0")],
    "Maintenance": [("Maintenance Cost", "SUM(Maintenance[TOTAL_COST])", "#,0"),
                    ("Maintenance Jobs", "COUNTROWS(Maintenance)", "#,0")],
    "Fuel": [("Fuel Cost", "SUM(Fuel[TOTAL_COST])", "#,0"),
             ("Avg km per unit", "AVERAGE(Fuel[KM_PER_UNIT])", "0.00"),
             ("Fill Count", "COUNTROWS(Fuel)", "#,0")],
    "Routes": [("Route Revenue", "SUM(Routes[REVENUE])", "#,0")],
    "KPI": [("Active Passes", "SUM(KPI[ACTIVE_PASSES])", "#,0"),
            ("Fleet Size", "SUM(KPI[TOTAL_BUSES])", "#,0")],
}
RELATIONSHIPS = [("RouteDay", "DATE_KEY", "DimDate", "DATE_KEY"), ("RouteDay", "ROUTE_ID", "Routes", "ROUTE_ID")]
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


def tmdl_type(dt: str, scale) -> tuple[str, str | None]:
    dt = dt.upper()
    if dt in ("NUMBER", "DECIMAL", "NUMERIC"):
        return ("int64", "0") if not scale else ("double", None)
    if dt in ("FLOAT", "DOUBLE", "REAL"):
        return "double", None
    if dt == "DATE":
        return "dateTime", "Long Date"
    if dt.startswith("TIMESTAMP"):
        return "dateTime", "General Date"
    if dt == "BOOLEAN":
        return "boolean", None
    return "string", None


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def jdump(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2))


# ---------------------------------------------------------------- semantic model (TMDL)
def build_model(cols: dict[str, list[tuple]]) -> None:
    jdump(SM / "definition.pbism", {"version": "4.0", "settings": {}})
    write(SM / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", ""]
    model += [f"ref table {t}" for t in TABLES] + [""]
    write(SM / "definition" / "model.tmdl", "\n".join(model))
    for t, (schema, view) in TABLES.items():
        L = [f"table {t}", f"\tlineageTag: {tag(t)}", ""]
        for mname, expr, fmt in MEASURES.get(t, []):
            L += [f"\tmeasure '{mname}' = {expr}", f"\t\tformatString: {fmt}", f"\t\tlineageTag: {tag(t, 'm', mname)}", ""]
        for cname, dt, scale in cols[t]:
            typ, fmt = tmdl_type(dt, scale)
            L += [f"\tcolumn {cname}", f"\t\tdataType: {typ}"]
            if fmt:
                L.append(f"\t\tformatString: {fmt}")
            numeric = typ in ("int64", "double") and not cname.endswith("_ID") and not cname.endswith(("YEAR", "_NO", "HOUR"))
            L += [f"\t\tlineageTag: {tag(t, cname)}", f"\t\tsummarizeBy: {'sum' if numeric else 'none'}",
                  f"\t\tsourceColumn: {cname}", "", "\t\tannotation SummarizationSetBy = Automatic", ""]
        m = [
            "let",
            f'    Source = Snowflake.Databases("{SERVER}", "{WAREHOUSE}"),',
            '    Db = Source{[Name = "BMTC_DW", Kind = "Database"]}[Data],',
            f'    Sch = Db{{[Name = "{schema}", Kind = "Schema"]}}[Data],',
            f'    Result = Sch{{[Name = "{view}", Kind = "View"]}}[Data]',
            "in",
            "    Result",
        ]
        L += [f"\tpartition {t} = m", "\t\tmode: import", "\t\tsource ="] + [f"\t\t\t\t{x}" for x in m]
        L += ["", "\tannotation PBI_ResultType = Table", ""]
        write(SM / "definition" / "tables" / f"{t}.tmdl", "\n".join(L))
    rel = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rel += [f"relationship {tag('rel', ft, fc, tt, tc)}", f"\tfromColumn: {ft}.{fc}", f"\ttoColumn: {tt}.{tc}", ""]
    write(SM / "definition" / "relationships.tmdl", "\n".join(rel))


# ---------------------------------------------------------------- report (PBIR)
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def col(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def mea(t, m):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": t}}, "Property": m}}


def proj(field, label=None):
    kind = "Column" if "Column" in field else "Measure"
    t, p = field[kind]["Expression"]["SourceRef"]["Entity"], field[kind]["Property"]
    out = {"field": field, "queryRef": f"{t}.{p}", "nativeQueryRef": p}
    if label:
        out["displayName"] = label
    return out


def lit(v: str):
    return {"expr": {"Literal": {"Value": v}}}


def visual(name, vtype, pos, roles: dict, title: str | None = None, sort=None, objects=None):
    x, y, w, h = pos
    v = {"visualType": vtype,
         "query": {"queryState": {r: {"projections": ps} for r, ps in roles.items()}},
         "drillFilterOtherVisuals": True}
    if sort:
        field, direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}], "isDefaultSort": True}
    if objects:
        v["objects"] = objects
    if title:
        v["visualContainerObjects"] = {"title": [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]}
    return {"$schema": f"{SCHEMA}/visualContainer/2.0.0/schema.json", "name": name,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}, "visual": v}


def build_report() -> None:
    jdump(RP / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    jdump(RP / "definition" / "version.json", {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    jdump(RP / "definition" / "report.json", {
        "$schema": f"{SCHEMA}/report/1.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.59", "type": "SharedResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]}],
    })
    jdump(RP / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU10.json", {
        "name": "CY24SU10", "dataColors": PALETTE + ["#3987e5", "#d95926", "#199e70", "#c98500"],
        "foreground": "#1e293b", "background": "#ffffff", "tableAccent": "#2a78d6",
        "good": "#0ca30c", "neutral": "#eda100", "bad": "#e34948",
        "maximum": "#184f95", "center": "#86b6ef", "minimum": "#cde2fb",
    })
    pages = {
        "overview": ("Operations Overview", [
            visual("c1", "card", (10, 10, 240, 110), {"Values": [proj(mea("RouteDay", "Total Trips"))]}, "Trips"),
            visual("c2", "card", (260, 10, 240, 110), {"Values": [proj(mea("RouteDay", "Total Passengers"))]}, "Passengers"),
            visual("c3", "card", (510, 10, 240, 110), {"Values": [proj(mea("RouteDay", "Total Revenue"))]}, "Ticket revenue (Rs)"),
            visual("c4", "card", (760, 10, 240, 110), {"Values": [proj(mea("RouteDay", "On-time %"))]}, "On-time trips"),
            visual("s1", "slicer", (1010, 10, 260, 110), {"Values": [proj(col("RouteDay", "DEPOT_NAME"), "Depot")]}, "Depot",
                   objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]}),
            visual("l1", "lineChart", (10, 130, 620, 285),
                   {"Category": [proj(col("DimDate", "YEAR_MONTH"), "Month")], "Y": [proj(mea("RouteDay", "Total Revenue"))]},
                   "Monthly ticket revenue (trend)", sort=(col("DimDate", "YEAR_MONTH"), "Ascending")),
            visual("b1", "clusteredBarChart", (640, 130, 630, 285),
                   {"Category": [proj(col("RouteDay", "DEPOT_NAME"), "Depot")], "Y": [proj(mea("RouteDay", "Total Revenue"))]},
                   "Revenue by depot (comparison)", sort=(mea("RouteDay", "Total Revenue"), "Descending")),
            visual("d1", "donutChart", (10, 425, 400, 285),
                   {"Category": [proj(col("RouteDay", "ROUTE_CATEGORY"), "Route category")], "Y": [proj(mea("RouteDay", "Total Revenue"))]},
                   "Revenue by route category"),
            visual("b2", "clusteredBarChart", (420, 425, 420, 285),
                   {"Category": [proj(col("Complaints", "CATEGORY"), "Category")], "Y": [proj(mea("Complaints", "Complaint Count"))]},
                   "Complaints by category (from JSON)", sort=(mea("Complaints", "Complaint Count"), "Descending")),
            visual("t1", "tableEx", (850, 425, 420, 285),
                   {"Values": [proj(col("Routes", "REVENUE_RANK"), "Rank"), proj(col("Routes", "ROUTE_CODE"), "Route"),
                               proj(col("Routes", "ROUTE_CATEGORY"), "Category"), proj(mea("Routes", "Route Revenue"), "Revenue")]},
                   "Route ranking - top to bottom", sort=(col("Routes", "REVENUE_RANK"), "Ascending")),
        ]),
        "fleet": ("Fleet, Fuel & Maintenance", [
            visual("c5", "card", (10, 10, 300, 110), {"Values": [proj(mea("KPI", "Fleet Size"))]}, "Buses"),
            visual("c6", "card", (320, 10, 300, 110), {"Values": [proj(mea("Fuel", "Fuel Cost"))]}, "Fuel / charging cost (Rs)"),
            visual("c7", "card", (630, 10, 300, 110), {"Values": [proj(mea("Maintenance", "Maintenance Cost"))]}, "Maintenance cost (Rs)"),
            visual("c8", "card", (940, 10, 330, 110), {"Values": [proj(mea("Complaints", "Open Complaints"))]}, "Open complaints"),
            visual("b3", "clusteredBarChart", (10, 130, 620, 285),
                   {"Category": [proj(col("Fuel", "BUS_TYPE"), "Bus type")], "Y": [proj(mea("Fuel", "Avg km per unit"))]},
                   "Fuel efficiency by bus type (km per L / kWh)", sort=(mea("Fuel", "Avg km per unit"), "Descending")),
            visual("k1", "clusteredColumnChart", (640, 130, 630, 285),
                   {"Category": [proj(col("Maintenance", "MAINTENANCE_TYPE"), "Type")], "Y": [proj(mea("Maintenance", "Maintenance Cost"))]},
                   "Maintenance cost by type", sort=(mea("Maintenance", "Maintenance Cost"), "Descending")),
            visual("k2", "stackedColumnChart", (10, 425, 620, 285),
                   {"Category": [proj(col("Fuel", "BUS_TYPE"), "Bus type")], "Series": [proj(col("Fuel", "EFFICIENCY_CLASS"), "Class")],
                    "Y": [proj(mea("Fuel", "Fill Count"))]},
                   "Python UDF efficiency class by bus type"),
            visual("t2", "tableEx", (640, 425, 630, 285),
                   {"Values": [proj(col("Buses", "REGISTRATION_NO"), "Bus"), proj(col("Buses", "BUS_TYPE"), "Type"),
                               proj(col("Buses", "DEPOT_NAME"), "Depot"), proj(col("Buses", "MAINTENANCE_COST"), "Maintenance cost"),
                               proj(col("Buses", "KM_PER_UNIT"), "km per unit")]},
                   "Costliest buses to maintain (top to bottom)", sort=(col("Buses", "MAINTENANCE_COST"), "Descending")),
        ]),
    }
    jdump(RP / "definition" / "pages" / "pages.json", {"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                       "pageOrder": list(pages), "activePageName": "overview"})
    for pid, (title, visuals) in pages.items():
        jdump(RP / "definition" / "pages" / pid / "page.json",
              {"$schema": f"{SCHEMA}/page/2.0.0/schema.json", "name": pid, "displayName": title,
               "displayOption": "FitToPage", "height": 720, "width": 1280})
        for v in visuals:
            jdump(RP / "definition" / "pages" / pid / "visuals" / v["name"] / "visual.json", v)


def main() -> None:
    for d in (SM, RP):
        if d.exists():
            shutil.rmtree(d)
    with connection() as conn:
        cols = {}
        for t, (schema, view) in TABLES.items():
            df = run_query(conn, """SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_SCALE FROM BMTC_DW.INFORMATION_SCHEMA.COLUMNS
                                    WHERE TABLE_SCHEMA = %(s)s AND TABLE_NAME = %(v)s ORDER BY ORDINAL_POSITION""",
                           {"s": schema, "v": view})
            if df.empty:
                raise SystemExit(f"View {schema}.{view} not found - run the SQL scripts first")
            cols[t] = [(r.COLUMN_NAME, r.DATA_TYPE, None if r.NUMERIC_SCALE != r.NUMERIC_SCALE else r.NUMERIC_SCALE)
                       for r in df.itertuples()]
    build_model(cols)
    build_report()
    jdump(OUT / f"{NAME}.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
                                 "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    n_vis = sum(1 for _ in RP.rglob("visual.json"))
    print(f"Wrote powerbi/{NAME}.pbip: {len(TABLES)} tables, {sum(len(v) for v in MEASURES.values())} measures, "
          f"{len(RELATIONSHIPS)} relationships, {n_vis} visuals")


if __name__ == "__main__":
    main()
