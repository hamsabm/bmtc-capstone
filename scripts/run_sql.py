"""Execute numbered SQL scripts against Snowflake and save an execution log.

Usage:
  venv\\Scripts\\python.exe scripts\\run_sql.py                 # run all sql/*.sql in order
  venv\\Scripts\\python.exe scripts\\run_sql.py 03 06           # run selected scripts by prefix
  venv\\Scripts\\python.exe scripts\\run_sql.py --keep-going 09 # do not stop at the first error

Conventions inside SQL files:
  {{DATA_DIR}}         replaced by the absolute path of ./data (used by PUT commands)
  -- @expect_error     placed inside a statement: the statement MUST fail (negative security tests)
  -- @optional         placed inside a statement: failure is logged as a limitation, not an error

Logs (no credentials) are written to logs/<script>.log.
"""
from __future__ import annotations

import argparse
import sys
import time
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snowflake.connector.util_text import split_statements  # noqa: E402

from utils.snowflake_connection import connect  # noqa: E402

SQL_DIR, LOG_DIR = ROOT / "sql", ROOT / "logs"
MAX_ROWS = 25


def fmt_rows(cur) -> str:
    if not cur.description:
        return f"   -> ok ({cur.rowcount} rows affected)" if cur.rowcount not in (None, -1) else "   -> ok"
    cols = [c[0] for c in cur.description]
    rows = cur.fetchmany(MAX_ROWS)
    out = ["   | " + " | ".join(cols)]
    out += ["   | " + " | ".join("NULL" if v is None else str(v)[:60] for v in r) for r in rows]
    more = cur.fetchall()
    if more:
        out.append(f"   | ... {len(more)} more rows")
    return "\n".join(out)


def run_file(conn, path: Path, keep_going: bool) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8").replace("{{DATA_DIR}}", (ROOT / "data").as_posix())
    log = StringIO()
    ok = failed = limits = 0
    print(f"\n=== {path.name}")
    log.write(f"# Execution log for {path.name} ({time.strftime('%Y-%m-%d %H:%M:%S')})\n")
    for stmt, _is_put in split_statements(StringIO(text), remove_comments=False):
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
        if not body:
            continue
        expect_error, optional = "@expect_error" in stmt, "@optional" in stmt
        head = " ".join(body.split())[:140]
        log.write(f"\n> {head}\n")
        try:
            is_transfer = body.upper().startswith(("PUT ", "GET "))
            for attempt in range(4 if is_transfer else 1):  # file transfers retry on network errors
                try:
                    with conn.cursor() as cur:
                        cur.execute(body)
                        result = fmt_rows(cur)
                    break
                except Exception:  # noqa: BLE001
                    if attempt == (3 if is_transfer else 0):
                        raise
                    print(f"    retrying file transfer (attempt {attempt + 2})")
                    time.sleep(5 * (attempt + 1))
            if expect_error:
                failed += 1
                msg = "   !! EXPECTED AN ERROR BUT STATEMENT SUCCEEDED"
                log.write(msg + "\n")
                print(f"FAIL (expected error) {head[:90]}")
            else:
                ok += 1
                log.write(result + "\n")
        except Exception as exc:  # noqa: BLE001
            err = " ".join(str(getattr(exc, "msg", exc)).split())[:400]
            if expect_error:
                ok += 1
                log.write(f"   -> expected error (PASS): {err}\n")
            elif optional:
                limits += 1
                log.write(f"   -> SKIPPED (optional statement; see MANUAL_STEPS.md if unexpected): {err}\n")
                print(f"SKIPPED (optional) {head[:80]}\n    {err}")
            else:
                failed += 1
                log.write(f"   !! ERROR: {err}\n")
                print(f"ERROR {head[:100]}\n    {err}")
                if not keep_going:
                    break
    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / f"{path.stem}.log").write_text(log.getvalue(), encoding="utf-8")
    print(f"    {ok} ok, {failed} failed, {limits} limitations -> logs/{path.stem}.log")
    return ok, failed, limits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prefixes", nargs="*")
    ap.add_argument("--keep-going", action="store_true")
    args = ap.parse_args()
    files = sorted(SQL_DIR.glob("*.sql"))
    if args.prefixes:
        explicit = [Path(p).resolve() for p in args.prefixes if p.endswith(".sql") and Path(p).exists()]
        files = explicit or [f for f in files if any(f.name.startswith(p) for p in args.prefixes)]
    # 01 creates the warehouse/database, so connect without them first
    conn = connect(warehouse=None, database=None, schema=None)
    total_failed = 0
    try:
        for f in files:
            _ok, failed, _lim = run_file(conn, f, args.keep_going)
            total_failed += failed
            if failed and not args.keep_going:
                break
    finally:
        conn.close()
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
