"""Deterministic SYNTHETIC BMTC academic dataset generator.

This is synthetic academic/demo data for a capstone project. It is NOT official
BMTC operational data. Names, registration numbers, phone numbers and e-mails
are fabricated.

Output (relative to project root):
  data/*.csv                              relational source files
  data/complaints.json                    NDJSON complaint documents (VARIANT)
  data/incremental/complaints_feed_001.json  new complaints for the Snowpipe demo

A small, documented set of data-quality problems is injected into the raw files
so that sql/03_data_loading.sql can detect and correct them (see INJECTED_ISSUES).
Re-running the script always produces identical files (fixed seed, fixed dates).
"""
from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 2026
START = date(2025, 11, 1)
END = date(2026, 10, 31)          # data "as-of" date
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
rng = random.Random(SEED)

INJECTED_ISSUES = """
Injected data-quality issues (detected and corrected in sql/03_data_loading.sql):
  trip_data.csv        5 exact duplicate rows; 3 rows with negative PASSENGER_COUNT (sign error)
  ticket_data.csv      10 exact duplicate rows; 3 orphan tickets referencing non-existent TRIP_IDs
  pass_data.csv        8 STATUS values with wrong case / whitespace; 4 rows with missing VALID_TO
  fuel_log.csv         4 rows with missing QUANTITY; 1 row with non-numeric QUANTITY ('twelve')
  maintenance_log.csv  3 rows with negative PARTS_COST (sign error)
""".strip()

# --------------------------------------------------------------------------- reference data
DEPOTS = [
    ("DPT-02", "Shanthinagar", "Central"), ("DPT-07", "Yeshwanthpur", "North"),
    ("DPT-12", "Kengeri", "West"), ("DPT-18", "Hebbal", "North"),
    ("DPT-21", "Banashankari", "South"), ("DPT-25", "Whitefield", "East"),
    ("DPT-28", "Electronic City", "South"), ("DPT-31", "Peenya", "West"),
    ("DPT-34", "Koramangala", "Central"), ("DPT-40", "Yelahanka", "North"),
]
STOPS = ["Kempegowda Bus Station", "Shivajinagar", "KR Market", "Jayanagar 4th Block", "Banashankari TTMC",
         "Kengeri TTMC", "Yeshwanthpur TTMC", "Hebbal", "Yelahanka", "Whitefield TTMC", "ITPL",
         "Marathahalli", "Silk Board", "Electronic City", "Koramangala", "HSR Layout", "BTM Layout",
         "Peenya", "Vijayanagar", "Rajajinagar", "Malleshwaram", "Indiranagar", "KR Puram", "Hoskote",
         "Kempegowda International Airport", "Bannerghatta", "JP Nagar", "Domlur", "Nagawara", "Attibele"]
# category -> (compatible bus types, fare per km, minimum fare, popularity factor)
CATEGORIES = {
    "City Ordinary": (["Ordinary"], 1.10, 6, 1.0),
    "Suburban": (["Ordinary"], 1.00, 10, 0.8),
    "Metro Feeder": (["Midi Feeder"], 0.90, 5, 0.9),
    "AC Vajra": (["Vajra AC", "Electric AC"], 2.20, 15, 0.7),
    "Airport Vayu Vajra": (["Vayu Vajra"], 7.50, 150, 0.45),
}
ROUTE_CATEGORY_PLAN = (["City Ordinary"] * 14 + ["AC Vajra"] * 8 + ["Metro Feeder"] * 8
                       + ["Suburban"] * 6 + ["Airport Vayu Vajra"] * 4)
BUS_MIX = ["Ordinary"] * 5 + ["Vajra AC"] * 2 + ["Vayu Vajra"] + ["Electric AC"] * 2 + ["Midi Feeder"] * 2
BUS_SPEC = {  # type -> (fuel, manufacturers, seats, base km per unit)
    "Ordinary": ("Diesel", ["Tata Motors", "Ashok Leyland"], 42, 3.6),
    "Midi Feeder": ("Diesel", ["Tata Motors", "Eicher"], 32, 4.6),
    "Vajra AC": ("Diesel", ["Volvo", "Scania"], 41, 2.6),
    "Vayu Vajra": ("Diesel", ["Volvo"], 45, 2.4),
    "Electric AC": ("Electric", ["Olectra", "Switch Mobility"], 35, 1.15),  # km per kWh
}
FIRST = ["Ravi", "Suresh", "Manjunath", "Lakshmi", "Kavya", "Prakash", "Nagaraj", "Anitha", "Shivakumar",
         "Deepa", "Ramesh", "Harish", "Pooja", "Mahesh", "Shwetha", "Girish", "Rekha", "Venkatesh",
         "Sunil", "Asha", "Naveen", "Divya", "Chandrashekar", "Meena", "Kiran", "Raghavendra",
         "Bhavya", "Santosh", "Nandini", "Arun", "Sowmya", "Vinay", "Geetha", "Mohan", "Rashmi"]
LAST = ["Gowda", "Reddy", "Rao", "Shetty", "Naik", "Hegde", "Kumar", "Murthy", "Patil", "Bhat",
        "Iyer", "Prasad", "Swamy", "Nayak", "Kulkarni", "Raju", "Sharma", "Achar", "Pai", "Devi"]
ROLES = [("Driver", 12, 28000, 42000), ("Conductor", 11, 22000, 34000), ("Mechanic", 3, 26000, 40000),
         ("Supervisor", 3, 38000, 52000), ("Depot Manager", 1, 65000, 90000)]
PASS_TYPES = {  # type -> (validity days, price, passenger category, weight)
    "Daily Pass": (1, 70, "General", 0.30),
    "Monthly General": (30, 1050, "General", 0.30),
    "Monthly Vajra": (30, 1800, "General", 0.12),
    "Student Pass": (180, 900, "Student", 0.18),
    "Senior Citizen Pass": (365, 600, "Senior Citizen", 0.10),
}


def d(x: date) -> str:
    return x.isoformat()


def ts(x: datetime) -> str:
    return x.strftime("%Y-%m-%d %H:%M:%S")


def name() -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def phone() -> str:
    return "9" + "".join(str(rng.randint(0, 9)) for _ in range(9))


def write_csv(fname: str, header: list[str], rows: list[list]) -> None:
    with open(DATA / fname, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows([["" if v is None else v for v in r] for r in rows])
    print(f"  {fname:<22} {len(rows):>7} rows")


# --------------------------------------------------------------------------- generation
def main() -> None:
    DATA.mkdir(exist_ok=True)
    (DATA / "incremental").mkdir(exist_ok=True)

    # Depots ---------------------------------------------------------------
    depots = []
    for i, (code, nm, zone) in enumerate(DEPOTS, 1):
        depots.append([i, code, f"{nm} Depot", zone, f"{nm}, Bengaluru", 120 + rng.randint(0, 8) * 10,
                       rng.randint(1975, 2015), phone()])

    # Buses: 12 per depot with a fixed mix -----------------------------------
    buses, bus_by_depot_type, bus_info = [], {}, {}
    bid = 0
    for dep in depots:
        for btype in BUS_MIX:
            bid += 1
            fuel, makers, seats, eff = BUS_SPEC[btype]
            year = rng.randint(2016, 2025) if btype != "Electric AC" else rng.randint(2022, 2025)
            commission = date(year, rng.randint(1, 12), rng.randint(1, 28))
            status = "ACTIVE"
            reg = f"KA-{rng.choice(['01', '02', '04', '05', '41', '51', '53', '57'])}-F-{rng.randint(1000, 9999)}"
            while any(b[1] == reg for b in buses):
                reg = f"KA-57-F-{rng.randint(1000, 9999)}"
            # efficiency factor: older buses less efficient, a few poor performers
            age = 2026 - year
            factor = (1 - 0.02 * age) * rng.uniform(0.92, 1.06) * (0.78 if rng.random() < 0.08 else 1)
            buses.append([bid, reg, btype, dep[0], rng.choice(makers), year, seats + rng.choice([-2, 0, 0, 2]),
                          fuel, status, d(commission)])
            bus_by_depot_type.setdefault((dep[0], btype), []).append(bid)
            bus_info[bid] = {"type": btype, "fuel": fuel, "eff": eff * factor, "depot": dep[0],
                             "age": age, "seats": buses[-1][6]}

    # Employees ------------------------------------------------------------
    employees, staff = [], {}
    eid = 0
    for dep in depots:
        for role, n, lo, hi in ROLES:
            for _ in range(n):
                eid += 1
                nm = name()
                join = START - timedelta(days=rng.randint(200, 9000))
                employees.append([eid, f"EMP{eid:05d}", nm, role, dep[0], d(join), phone(),
                                  f"{nm.lower().replace(' ', '.')}{eid}@bmtc-demo.example",
                                  round(rng.uniform(lo, hi) / 100) * 100, "ACTIVE"])
                staff.setdefault((dep[0], role), []).append(eid)
    for e in rng.sample(employees, 9):
        e[9] = "ON_LEAVE"

    # Routes: 4 per depot -------------------------------------------------
    routes, route_info = [], {}
    cats = ROUTE_CATEGORY_PLAN[:]
    rng.shuffle(cats)
    # guarantee every depot can serve its routes: airport routes only at depots with Vayu Vajra (all have 1)
    used_codes = set()
    for rid in range(1, 41):
        cat = cats[rid - 1]
        depot_id = (rid - 1) // 4 + 1
        src = DEPOTS[depot_id - 1][1]
        src_stop = next((s for s in STOPS if s.startswith(src.split()[0])), rng.choice(STOPS))
        if cat == "Airport Vayu Vajra":
            dst = "Kempegowda International Airport"
            dist = round(rng.uniform(32, 48), 1)
        else:
            dst = rng.choice([s for s in STOPS if s not in (src_stop, "Kempegowda International Airport")])
            dist = round(rng.uniform(8, 22) if cat in ("City Ordinary", "Metro Feeder") else rng.uniform(15, 38), 1)
        prefix = {"City Ordinary": "", "Suburban": "", "Metro Feeder": "MF-", "AC Vajra": "V-",
                  "Airport Vayu Vajra": "KIA-"}[cat]
        code = f"{prefix}{rng.randint(100, 599)}{rng.choice(['', 'A', 'B', 'C', 'D', 'E'])}"
        while code in used_codes:
            code = f"{prefix}{rng.randint(100, 599)}{rng.choice(['', 'K', 'M'])}"
        used_codes.add(code)
        _, rate, min_fare, pop = CATEGORIES[cat]
        base = max(min_fare, round(rate * dist / 5) * 5)
        stops = max(6, int(dist * rng.uniform(1.0, 1.6)))
        active = rid not in (17, 33)  # two routes discontinued (no trips) -> LEFT JOIN demo
        routes.append([rid, code, f"{src_stop} - {dst}", src_stop, dst, dist, stops, cat, base, depot_id,
                       "TRUE" if active else "FALSE"])
        route_info[rid] = {"cat": cat, "dist": dist, "depot": depot_id, "pop": pop * rng.uniform(0.5, 1.9),
                           "base": base, "rate": rate, "min": min_fare, "active": active}

    # Passes --------------------------------------------------------------
    passes, pass_by_kind = [], {}
    ptypes = list(PASS_TYPES)
    weights = [PASS_TYPES[p][3] for p in ptypes]
    for pid in range(1, 1501):
        ptype = rng.choices(ptypes, weights)[0]
        days, price, pcat, _ = PASS_TYPES[ptype]
        issue = START - timedelta(days=60) + timedelta(days=rng.randint(0, (END - START).days + 60))
        valid_from = issue + timedelta(days=rng.choice([0, 0, 0, 1]))
        valid_to = valid_from + timedelta(days=days - 1)
        status = "CANCELLED" if rng.random() < 0.02 else ("ACTIVE" if valid_to >= END else "EXPIRED")
        nm = name()
        email = f"{nm.lower().replace(' ', '.')}.{pid}@mail-demo.example" if rng.random() > 0.15 else None
        passes.append([pid, f"BMTC-P-{pid:06d}", nm, phone(), email, ptype, pcat, d(issue), d(valid_from),
                       d(valid_to), price, rng.randint(1, len(depots)), status])
        pass_by_kind.setdefault("vajra" if ptype == "Monthly Vajra" else "general", []).append(
            (pid, valid_from, valid_to, status, pcat))

    # Trips + tickets -----------------------------------------------------
    trips, tickets = [], []
    active_routes = [r for r in route_info if route_info[r]["active"]]
    rweights = [route_info[r]["pop"] for r in active_routes]
    hours = list(range(5, 23))
    hweights = [0.4, 0.8, 1.4, 2.4, 2.6, 1.6, 1.0, 0.9, 0.9, 1.0, 1.0, 1.2, 1.8, 2.5, 2.6, 1.8, 1.0, 0.5]
    tid = tkid = 0
    day = START
    trip_meta = {}
    while day <= END:
        weekday = day.weekday() < 5
        month_factor = 1 + 0.10 * math.sin((day.month - 3) / 12 * 2 * math.pi)  # mild seasonality
        n_trips = int(round((12 if weekday else 8) * month_factor + rng.uniform(-1.5, 1.5)))
        for _ in range(n_trips):
            tid += 1
            rid = rng.choices(active_routes, rweights)[0]
            ri = route_info[rid]
            btype = rng.choice(CATEGORIES[ri["cat"]][0])
            bus = rng.choice(bus_by_depot_type[(ri["depot"], btype)])
            driver = rng.choice(staff[(ri["depot"], "Driver")])
            conductor = rng.choice(staff[(ri["depot"], "Conductor")])
            hour = rng.choices(hours, hweights)[0]
            sched = datetime(day.year, day.month, day.day, hour, rng.choice(range(0, 60, 5)))
            peak = hour in (8, 9, 17, 18, 19)
            delay = max(0, int(rng.expovariate(1 / (14 if peak else 5)) - (0 if peak else 2)))
            speed = rng.uniform(12, 17) if peak else rng.uniform(18, 26)
            if ri["cat"] == "Airport Vayu Vajra":
                speed += 8
            r = rng.random()
            status = "CANCELLED" if r < 0.025 else ("BREAKDOWN" if r < 0.035 else "COMPLETED")
            start = sched + timedelta(minutes=delay)
            dist_run = ri["dist"] if status == "COMPLETED" else (0 if status == "CANCELLED"
                                                                  else round(ri["dist"] * rng.uniform(0.2, 0.8), 1))
            duration = int(dist_run / speed * 60) if dist_run else 0
            if status == "CANCELLED":
                pax, astart, aend, delay_out = 0, None, None, None
            else:
                load = ri["pop"] * (1.7 if peak else 1.0) * (1.15 if weekday else 0.8) * month_factor
                pax = max(3, int(rng.gauss(18 * load, 5)))
                pax = min(pax, int(bus_info[bus]["seats"] * 1.6))
                if status == "BREAKDOWN":
                    pax = max(2, pax // 2)
                astart, aend, delay_out = ts(start), ts(start + timedelta(minutes=duration)), delay
            trips.append([tid, bus, rid, driver, conductor, d(day), ts(sched), astart, aend, delay_out,
                          pax, dist_run, status])
            trip_meta[tid] = {"route": rid, "bus": bus, "day": day, "start": start, "dur": max(duration, 5),
                              "pax": pax, "delay": delay_out or 0, "status": status,
                              "occ": pax / bus_info[bus]["seats"], "dist": dist_run}
            # one ticket row per passenger boarding (pass validations included)
            for _ in range(pax):
                tkid += 1
                t_ts = start + timedelta(minutes=rng.randint(0, max(duration - 3, 1)))
                frac = rng.uniform(0.15, 1.0)
                pcat = rng.choices(["Adult", "Student", "Senior Citizen", "Child"], [0.72, 0.14, 0.08, 0.06])[0]
                pass_id = None
                if rng.random() < 0.16:
                    pool = pass_by_kind["vajra" if ri["cat"] == "AC Vajra" else "general"]
                    for _try in range(12):
                        p = rng.choice(pool)
                        if p[1] <= day <= p[2] and p[3] != "CANCELLED":
                            pass_id = p[0]
                            pcat = {"Student": "Student", "Senior Citizen": "Senior Citizen"}.get(p[4], "Adult")
                            break
                if pass_id:
                    ttype, fare, pay = "Pass Validation", 0, "Pass"
                else:
                    fare = max(ri["min"], round(ri["rate"] * ri["dist"] * frac))
                    fare *= {"Adult": 1, "Student": 0.75, "Senior Citizen": 0.75, "Child": 0.5}[pcat]
                    fare = int(round(fare))
                    ttype = "Single Journey"
                    pay = rng.choices(["UPI", "Cash", "Card"], [0.5, 0.38, 0.12])[0]
                tickets.append([tkid, f"TKT{tkid:08d}", tid, rid, ts(t_ts), d(day), ttype, pcat,
                                round(ri["dist"] * frac, 1), fare, pay, pass_id])
        day += timedelta(days=1)

    # Fuel: refuel when km since last fill crosses a bus-specific threshold ----------------
    fuel, fid = [], 0
    unit_price = {"Diesel": 89.0, "Electric": 9.5}
    km_by_bus_day: dict[int, dict[date, float]] = {}
    for t in trips:
        if t[11]:
            km_by_bus_day.setdefault(t[1], {}).setdefault(trip_meta[t[0]]["day"], 0)
            km_by_bus_day[t[1]][trip_meta[t[0]]["day"]] += t[11] * 1.08  # +8% dead mileage
    events = []
    for bus, days_km in km_by_bus_day.items():
        info = bus_info[bus]
        odo = 40000 * info["age"] + rng.randint(5000, 30000)
        acc, threshold = 0.0, rng.uniform(140, 220)
        for dday in sorted(days_km):
            acc += days_km[dday]
            if acc >= threshold:
                qty = round(acc / (info["eff"] * rng.uniform(0.94, 1.06)), 1)
                odo += acc
                events.append((dday, bus, info, qty, acc, odo))
                acc, threshold = 0.0, rng.uniform(140, 220)
    events.sort(key=lambda e: (e[0], e[1]))
    for dday, bus, info, qty, acc, odo in events:
        fid += 1
        price = unit_price[info["fuel"]] + round(rng.uniform(-1.5, 1.5) if info["fuel"] == "Diesel" else 0, 2)
        fuel.append([fid, bus, info["depot"], d(dday), info["fuel"], "LITRE" if info["fuel"] == "Diesel" else "KWH",
                     qty, price, round(qty * price, 2), round(odo, 1), round(acc, 1),
                     f"{DEPOTS[info['depot'] - 1][1]} Depot {'Fuel Station' if info['fuel'] == 'Diesel' else 'Charging Hub'}"])

    # Maintenance -------------------------------------------------------
    maint = []
    MTYPES = {"Preventive Service": (2500, 6000, 4, "LOW"), "Brake Repair": (4000, 12000, 8, "MEDIUM"),
              "Tyre Replacement": (18000, 32000, 5, "MEDIUM"), "Engine Repair": (25000, 90000, 36, "HIGH"),
              "Electrical Fault": (3000, 15000, 10, "MEDIUM"), "AC Repair": (6000, 22000, 12, "MEDIUM"),
              "Battery Service": (8000, 40000, 16, "HIGH"), "Body Work": (5000, 25000, 20, "LOW")}
    for bus, info in bus_info.items():
        nxt = START + timedelta(days=rng.randint(0, 80))
        while nxt <= END:
            maint.append([bus, nxt, "Preventive Service"])
            nxt += timedelta(days=rng.randint(80, 100))
        n_corr = rng.choices([0, 1, 2, 3], [0.3, 0.4, 0.2, 0.1])[0] + (1 if info["age"] >= 7 else 0)
        for _ in range(n_corr):
            opts = ["Brake Repair", "Tyre Replacement", "Electrical Fault", "Body Work"]
            opts += ["AC Repair"] if info["type"] in ("Vajra AC", "Vayu Vajra", "Electric AC") else []
            opts += ["Battery Service"] if info["fuel"] == "Electric" else ["Engine Repair"]
            maint.append([bus, START + timedelta(days=rng.randint(0, (END - START).days)), rng.choice(opts)])
    for t in trips:
        if t[12] == "BREAKDOWN":
            b = bus_info[t[1]]
            mtype = rng.choice(["Battery Service", "Electrical Fault"] if b["fuel"] == "Electric"
                               else ["Engine Repair", "Electrical Fault", "Brake Repair"])
            maint.append([t[1], trip_meta[t[0]]["day"] + timedelta(days=1), mtype, "BREAKDOWN"])
    maint = [m for m in maint if m[1] <= END]
    maint.sort(key=lambda m: (m[1], m[0]))
    maintenance = []
    for mid, m in enumerate(maint, 1):
        bus, mdate, mtype = m[0], m[1], m[2]
        lo, hi, down, sev = MTYPES[mtype]
        age_f = 1 + 0.04 * bus_info[bus]["age"]
        parts = round(rng.uniform(lo, hi) * age_f * 0.7, -1)
        labour = round(rng.uniform(lo, hi) * 0.3, -1)
        if len(m) > 3:
            sev = "CRITICAL"
        elif sev == "MEDIUM" and rng.random() < 0.2:
            sev = "HIGH"
        mech = rng.choice(staff[(bus_info[bus]["depot"], "Mechanic")])
        status = "IN_PROGRESS" if (END - mdate).days < 3 and mtype != "Preventive Service" else "COMPLETED"
        desc = {"Preventive Service": "Scheduled service: oil, filters, inspection",
                "Brake Repair": "Brake pads/liners replaced after inspection",
                "Tyre Replacement": "Rear tyre set replaced", "Engine Repair": "Engine overheating / power loss repaired",
                "Electrical Fault": "Wiring and lighting fault rectified", "AC Repair": "AC compressor/gas service",
                "Battery Service": "Traction battery diagnostics and cell balancing",
                "Body Work": "Panel and seat repair"}[mtype]
        if len(m) > 3:
            desc = "On-road breakdown: " + desc
        maintenance.append([mid, bus, d(mdate), mtype, desc, parts, labour, round(parts + labour, 2),
                            round(down * rng.uniform(0.6, 1.6), 1), sev, mech, status])

    # Complaints (JSON) --------------------------------------------------
    complaint_sub = {
        "Delay": ["Late departure", "Bus did not arrive", "Long wait at stop"],
        "Overcrowding": ["No standing space", "Bus skipped stop due to crowd"],
        "Staff Behaviour": ["Rude conductor", "Driver used phone", "Refused to stop"],
        "Ticketing": ["Change not returned", "UPI payment failed", "Overcharged fare"],
        "Cleanliness": ["Dirty seats", "Littered floor"],
        "Safety": ["Rash driving", "Door open while moving", "Harassment reported"],
        "Bus Condition": ["Broken seat", "Window not closing", "Leaking roof"],
        "AC Not Working": ["AC not cooling", "AC switched off"],
    }
    prio = {"Safety": "High", "Staff Behaviour": "Medium", "Delay": "Medium", "Overcrowding": "Medium",
            "Ticketing": "Low", "Cleanliness": "Low", "Bus Condition": "Low", "AC Not Working": "Medium"}
    tlist = [t for t in trips if t[12] != "CANCELLED"] + [t for t in trips if t[12] == "CANCELLED"] * 3
    cweights = [1 + trip_meta[t[0]]["delay"] / 8 + max(0, trip_meta[t[0]]["occ"] - 1) * 4 for t in tlist]
    route_code = {r[0]: r[1] for r in routes}

    def complaint(cid: int, t: list, as_of: date) -> dict:
        m = trip_meta[t[0]]
        ac = bus_info[m["bus"]]["type"] in ("Vajra AC", "Vayu Vajra", "Electric AC")
        if m["status"] == "CANCELLED" or m["delay"] > 15:
            cat = "Delay" if rng.random() < 0.7 else rng.choice(list(complaint_sub))
        elif m["occ"] > 1.15 and rng.random() < 0.6:
            cat = "Overcrowding"
        else:
            cat = rng.choice([c for c in complaint_sub if c not in ("Delay", "Overcrowding")
                              and (ac or c != "AC Not Working")])
        sub = rng.choice(complaint_sub[cat])
        submitted = m["start"] + timedelta(minutes=m["dur"] + rng.randint(5, 60 * 30))
        p = prio[cat] if rng.random() > 0.2 else rng.choice(["Low", "Medium", "High"])
        age_days = (as_of - submitted.date()).days
        status = rng.choices(["Resolved", "In Progress", "Open", "Rejected"], [0.74, 0.12, 0.08, 0.06])[0]
        if age_days < 5:
            status = rng.choice(["Open", "In Progress"])
        res_days = rng.randint(1, 4 if p == "High" else 12) if status in ("Resolved", "Rejected") else None
        pid = None
        if rng.random() < 0.55:
            pid = rng.choice(passes)[0]
        stop = rng.choice(STOPS)
        doc = {
            "complaint_id": f"CMP-{cid:06d}",
            "submitted_at": ts(submitted),
            "channel": rng.choices(["Mobile App", "Helpline 1800-425-1663", "Twitter/X", "Depot Counter", "Email"],
                                   [0.45, 0.25, 0.12, 0.10, 0.08])[0],
            "category": cat,
            "sub_category": sub,
            "priority": p,
            "description": f"{sub} on route {route_code[m['route']]} near {stop}.",
            "passenger": {"pass_id": pid, "is_registered": pid is not None,
                          "language": rng.choice(["Kannada", "English", "Hindi", "Tamil", "Telugu"])},
            "service": {"trip_id": t[0], "route_id": m["route"], "route_code": route_code[m["route"]],
                        "bus_id": m["bus"], "depot_id": bus_info[m["bus"]]["depot"], "trip_date": d(m["day"])},
            "location": {"stop_name": stop, "geo": {"lat": round(12.85 + rng.random() * 0.3, 5),
                                                    "lon": round(77.45 + rng.random() * 0.35, 5)}},
            "tags": sorted(set(rng.sample(["peak-hour", "repeat", "women-safety", "senior-citizen", "student",
                                           "night", "weekend", "photo-attached"], rng.randint(0, 3)))),
            "resolution": {
                "status": status,
                "assigned_to": {"depot_id": bus_info[m["bus"]]["depot"],
                                "employee_id": rng.choice(staff[(bus_info[m["bus"]]["depot"], "Supervisor")])},
                "resolution_days": res_days,
                "resolved_at": ts(submitted + timedelta(days=res_days)) if res_days else None,
                "satisfaction_rating": rng.randint(1, 5) if status == "Resolved" else None,
            },
        }
        return doc

    complaints = []
    chosen = rng.choices(tlist, cweights, k=460)
    chosen.sort(key=lambda t: trip_meta[t[0]]["start"])
    for i, t in enumerate(chosen, 1):
        complaints.append(complaint(i, t, END))
    # incremental feed (Snowpipe demo): 25 complaints about the final week
    recent = [t for t in trips if trip_meta[t[0]]["day"] > END - timedelta(days=7)]
    feed = [complaint(461 + i, t, END) for i, t in enumerate(rng.sample(recent, 25))]

    # ----------------------------------------------------------------- inject quality issues
    for r in rng.sample(trips, 3):
        r[10] = -r[10] if r[10] else -5  # sign error; rows with 0 pax are cancelled -> pick non-zero
    trips_out = trips + [list(r) for r in rng.sample(trips, 5)]
    tickets_out = tickets + [list(r) for r in rng.sample(tickets, 10)]
    for k in range(3):
        tkid += 1
        tickets_out.append([tkid, f"TKT{tkid:08d}", 999990 + k, 1, "2026-10-30 10:00:00", "2026-10-30",
                            "Single Journey", "Adult", 5.0, 10, "Cash", None])
    for r in rng.sample(passes, 8):
        r[12] = rng.choice([f" {r[12].lower()}", r[12].title(), f"{r[12]} "])
    for r in rng.sample(passes, 4):
        r[9] = None
    for r in rng.sample(fuel, 4):
        r[6] = None
    bad = list(rng.choice(fuel))
    bad[0], bad[6] = len(fuel) + 1, "twelve"
    fuel_out = fuel + [bad]
    for r in rng.sample(maintenance, 3):
        r[5] = -r[5]

    # ----------------------------------------------------------------- write files
    print("Writing synthetic BMTC academic dataset to", DATA)
    write_csv("depot_master.csv", ["DEPOT_ID", "DEPOT_CODE", "DEPOT_NAME", "ZONE", "ADDRESS", "BUS_CAPACITY",
                                   "ESTABLISHED_YEAR", "CONTACT_PHONE"], depots)
    write_csv("bus_master.csv", ["BUS_ID", "REGISTRATION_NO", "BUS_TYPE", "DEPOT_ID", "MANUFACTURER",
                                 "MANUFACTURE_YEAR", "SEATING_CAPACITY", "FUEL_TYPE", "STATUS",
                                 "COMMISSION_DATE"], buses)
    write_csv("employee_master.csv", ["EMPLOYEE_ID", "EMPLOYEE_CODE", "EMPLOYEE_NAME", "ROLE", "DEPOT_ID",
                                      "JOIN_DATE", "PHONE", "EMAIL", "MONTHLY_SALARY", "STATUS"], employees)
    write_csv("route_master.csv", ["ROUTE_ID", "ROUTE_CODE", "ROUTE_NAME", "SOURCE_STOP", "DESTINATION_STOP",
                                   "DISTANCE_KM", "NUM_STOPS", "ROUTE_CATEGORY", "BASE_FARE", "DEPOT_ID",
                                   "ACTIVE_FLAG"], routes)
    write_csv("trip_data.csv", ["TRIP_ID", "BUS_ID", "ROUTE_ID", "DRIVER_ID", "CONDUCTOR_ID", "TRIP_DATE",
                                "SCHEDULED_START", "ACTUAL_START", "ACTUAL_END", "DELAY_MINUTES",
                                "PASSENGER_COUNT", "DISTANCE_KM", "TRIP_STATUS"], trips_out)
    write_csv("ticket_data.csv", ["TICKET_ID", "TICKET_NO", "TRIP_ID", "ROUTE_ID", "TICKET_TS", "TICKET_DATE",
                                  "TICKET_TYPE", "PASSENGER_CATEGORY", "TRAVEL_KM", "FARE", "PAYMENT_MODE",
                                  "PASS_ID"], tickets_out)
    write_csv("fuel_log.csv", ["FUEL_ID", "BUS_ID", "DEPOT_ID", "FUEL_DATE", "FUEL_TYPE", "UNIT", "QUANTITY",
                               "UNIT_PRICE", "TOTAL_COST", "ODOMETER_KM", "KM_SINCE_LAST_FILL", "STATION"],
              fuel_out)
    write_csv("maintenance_log.csv", ["MAINTENANCE_ID", "BUS_ID", "MAINTENANCE_DATE", "MAINTENANCE_TYPE",
                                      "DESCRIPTION", "PARTS_COST", "LABOUR_COST", "TOTAL_COST", "DOWNTIME_HOURS",
                                      "SEVERITY", "MECHANIC_ID", "STATUS"], maintenance)
    write_csv("pass_data.csv", ["PASS_ID", "PASS_NUMBER", "PASSENGER_NAME", "PHONE", "EMAIL", "PASS_TYPE",
                                "PASSENGER_CATEGORY", "ISSUE_DATE", "VALID_FROM", "VALID_TO", "PRICE",
                                "ISSUING_DEPOT_ID", "STATUS"], passes)
    with open(DATA / "complaints.json", "w", encoding="utf-8") as fh:
        for c in complaints:
            fh.write(json.dumps(c) + "\n")
    print(f"  complaints.json        {len(complaints):>7} docs")
    with open(DATA / "incremental" / "complaints_feed_001.json", "w", encoding="utf-8") as fh:
        for c in feed:
            fh.write(json.dumps(c) + "\n")
    print(f"  incremental feed       {len(feed):>7} docs")
    (DATA / "README.md").write_text(
        "# Synthetic BMTC academic dataset\n\nGenerated by `scripts/generate_data.py` (seed "
        f"{SEED}, window {START} to {END}).\n\n**This is synthetic academic/demo data, not official BMTC "
        "operational data.** All names, phone numbers, e-mails and registration numbers are fabricated.\n\n```\n"
        + INJECTED_ISSUES + "\n```\n", encoding="utf-8")


if __name__ == "__main__":
    main()
