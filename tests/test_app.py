r"""Headless smoke test of every Streamlit page against live Snowflake.
Run: venv\Scripts\python.exe tests\test_app.py"""
from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app.py"] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "app_pages").glob("*.py"))


def run_page(path: str):
    at = AppTest.from_file(str(ROOT / path), default_timeout=180)
    at.run()
    errors = [e.value for e in at.error]
    exceptions = [str(e.value)[:300] for e in at.exception]
    charts = len(at.get("plotly_chart"))
    tables = len(at.dataframe)
    metrics = len(at.metric)
    return errors, exceptions, charts, tables, metrics


def test_pages():
    for p in PAGES:
        errors, exceptions, *_ = run_page(p)
        assert not errors and not exceptions, (p, errors, exceptions)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    failed = 0
    for p in PAGES:
        errors, exceptions, charts, tables, metrics = run_page(p)
        ok = not errors and not exceptions
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {p:<36} charts={charts:<3} tables={tables:<3} metrics={metrics:<3}"
              + ("" if ok else f"\n      errors={errors}\n      exceptions={exceptions}"))
    sys.exit(1 if failed else 0)
