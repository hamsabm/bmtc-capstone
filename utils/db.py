"""Streamlit data-access layer: one cached Snowflake connection, cached reads,
parameterised writes, and friendly error handling."""
from __future__ import annotations

import threading

import pandas as pd
import streamlit as st

from utils.snowflake_connection import SnowflakeConfigError, connect, run_query

_LOCK = threading.Lock()


@st.cache_resource(show_spinner=False)
def _connection():
    return connect()


def _run(sql: str, params) -> pd.DataFrame:
    with _LOCK:
        try:
            return run_query(_connection(), sql, params)
        except Exception as exc:  # stale/closed session -> reconnect once
            if "session" in str(exc).lower() or "connection" in str(exc).lower():
                _connection.clear()
                return run_query(_connection(), sql, params)
            raise


@st.cache_data(ttl=600, show_spinner="Querying Snowflake...")
def cached_query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    return _run(sql, dict(params) if params and isinstance(params[0], tuple) else params)


def query(sql: str, params: dict | tuple | None = None, cache: bool = True) -> pd.DataFrame:
    """Run a read query. Returns an empty DataFrame (and shows an error) on failure."""
    try:
        if cache:
            key = tuple(sorted(params.items())) if isinstance(params, dict) else params
            return cached_query(sql, key)
        return _run(sql, params)
    except SnowflakeConfigError as exc:
        st.error(f"Configuration problem: {exc}")
    except ConnectionError as exc:
        st.error(f"Snowflake connection failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Query failed: {getattr(exc, 'msg', None) or exc}")
    return pd.DataFrame()


def execute(statements: list[tuple[str, dict | None]]) -> int:
    """Run several DML statements in ONE transaction (BEGIN ... COMMIT / ROLLBACK).
    Returns total affected rows; raises on failure after rolling back."""
    total = 0
    with _LOCK:
        conn = _connection()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            for sql, params in statements:
                cur.execute(sql, params)
                total += max(cur.rowcount or 0, 0)
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            cur.close()
    cached_query.clear()
    return total


def connection_ok() -> tuple[bool, str]:
    try:
        df = _run("SELECT CURRENT_ACCOUNT() A, CURRENT_ROLE() R, CURRENT_WAREHOUSE() W, CURRENT_DATABASE() D", None)
        r = df.iloc[0]
        return True, f"Account {r.A} | role {r.R} | warehouse {r.W} | database {r.D}"
    except Exception as exc:  # noqa: BLE001
        return False, str(getattr(exc, "msg", None) or exc)
