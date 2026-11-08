r"""Navigation through app.py (st.navigation) and clean handling of an unreachable Snowflake.
Run: venv\Scripts\python.exe tests\test_navigation_errors.py"""
import os
import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["pages/1_Dashboard.py", "pages/2_Bus_Management.py", "pages/3_Routes_Trips.py",
         "pages/4_Ticket_Analytics.py", "pages/5_Fuel_Maintenance.py", "pages/6_Passenger_Complaints.py",
         "pages/7_Advanced_Analytics.py", "pages/8_Data_Management.py"]

if len(sys.argv) > 1 and sys.argv[1] == "--broken":
    # child process: environment points at a non-existent account
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    msgs = [e.value for e in at.error]
    ok = (not at.exception and len(msgs) == 1 and "Cannot reach Snowflake" in msgs[0]
          and len(at.metric) == 0 and len(at.get("plotly_chart")) == 0)
    print("BROKEN_OK" if ok else f"BROKEN_FAIL errors={msgs} exceptions={[str(x.value)[:200] for x in at.exception]}")
    sys.exit(0)

results = []
at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
at.run()
results.append(("Home via app.py", not at.exception and not at.error and at.title[0].value.startswith("BMTC")))
for p in PAGES:
    at.switch_page(p).run()
    results.append((f"Navigate to {p}", not at.exception and not at.error and len(at.title) == 1))

env = dict(os.environ, SNOWFLAKE_ACCOUNT="invalid-account-bmtc-test", SNOWFLAKE_USER="nobody",
           SNOWFLAKE_PASSWORD="not-a-real-password")
out = subprocess.run([sys.executable, __file__, "--broken"], env=env, capture_output=True, text=True, timeout=300)
results.append(("Unreachable Snowflake -> single clean error, no traceback, no fake KPIs", "BROKEN_OK" in out.stdout))

for name, ok in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
if "BROKEN_OK" not in out.stdout:
    print(out.stdout[-800:])
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} navigation/error checks passed")
sys.exit(1 if failed else 0)
