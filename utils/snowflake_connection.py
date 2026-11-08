"""Snowflake connection helpers for the BMTC capstone.

Configuration comes from environment variables, loaded from the local .env file
(python-dotenv) or, when deployed, from Streamlit secrets. Two authentication modes:
  * password:  SNOWFLAKE_PASSWORD
  * key-pair:  SNOWFLAKE_PRIVATE_KEY (PEM text) or SNOWFLAKE_PRIVATE_KEY_FILE (path)
               - used by the least-privilege service user for public deployment.
Nothing in this module prints or logs secrets.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

KEYS = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_PRIVATE_KEY",
        "SNOWFLAKE_PRIVATE_KEY_FILE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_ROLE")


class SnowflakeConfigError(RuntimeError):
    """Raised when required settings are missing."""


def _get(key: str, default: str | None = None) -> str | None:
    """Environment first; then Streamlit secrets (Streamlit Community Cloud)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st

        # Silent probe that honours every location Streamlit reads secrets from (incl. Streamlit Cloud)
        if not st.secrets.load_if_toml_exists():
            return default
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # noqa: BLE001 - no secrets file / not running under Streamlit
        pass
    return default


def config_sources() -> str:
    """Where Snowflake settings were found - key NAMES only, never values (for troubleshooting)."""
    env_keys = [k for k in KEYS if os.getenv(k)]
    try:
        import streamlit as st

        if st.secrets.load_if_toml_exists():
            sec = [k for k in st.secrets.keys() if str(k).startswith("SNOWFLAKE_")]
            secrets_txt = f"loaded, Snowflake keys: {', '.join(sorted(sec)) or 'none'}"
        else:
            secrets_txt = "not found"
    except Exception:  # noqa: BLE001
        secrets_txt = "unavailable"
    return f"Environment keys: {', '.join(env_keys) or 'none'} | Streamlit secrets: {secrets_txt}"


def _private_key_der() -> bytes | None:
    pem = _get("SNOWFLAKE_PRIVATE_KEY")
    path = _get("SNOWFLAKE_PRIVATE_KEY_FILE")
    if not pem and path:
        p = Path(path) if Path(path).is_absolute() else ROOT / path
        pem = p.read_text(encoding="utf-8")
    if not pem:
        return None
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(pem.encode(), password=None)
    return key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def settings(role: str | None = None) -> dict:
    key_der = _private_key_der()
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER"] + ([] if key_der else ["SNOWFLAKE_PASSWORD"])
    missing = [k for k in required if not _get(k)]
    if missing:
        raise SnowflakeConfigError(f"Missing Snowflake settings: {', '.join(missing)}")
    cfg = {
        "account": _get("SNOWFLAKE_ACCOUNT"),
        "user": _get("SNOWFLAKE_USER"),
        "warehouse": _get("SNOWFLAKE_WAREHOUSE", "BMTC_WH"),
        "database": _get("SNOWFLAKE_DATABASE", "BMTC_DW"),
        "schema": _get("SNOWFLAKE_SCHEMA", "BUS"),
        "login_timeout": 30,
        "network_timeout": 120,
        "client_session_keep_alive": True,
        "application": "BMTC_CAPSTONE",
    }
    if key_der:   # key-pair takes precedence over a password
        cfg["authenticator"] = "SNOWFLAKE_JWT"
        cfg["private_key"] = key_der
    else:
        cfg["password"] = _get("SNOWFLAKE_PASSWORD")
    role = role or _get("SNOWFLAKE_ROLE")
    if role:
        cfg["role"] = role
    return cfg


def connect(role: str | None = None, **overrides):
    """Open a new Snowflake connection. Errors are re-raised without credential details."""
    import snowflake.connector
    from snowflake.connector.errors import Error as SnowflakeError

    cfg = settings(role)
    cfg.update(overrides)
    cfg = {k: v for k, v in cfg.items() if v is not None}
    try:
        return snowflake.connector.connect(**cfg)
    except SnowflakeError as exc:
        msg = getattr(exc, "msg", None) or str(exc)
        raise ConnectionError(f"Unable to connect to Snowflake ({cfg['account']}): {msg}") from None


@contextmanager
def connection(role: str | None = None) -> Iterator[object]:
    conn = connect(role)
    try:
        yield conn
    finally:
        conn.close()


def _to_frame(cur) -> pd.DataFrame:
    cols = [c[0] for c in cur.description] if cur.description else []
    df = pd.DataFrame(cur.fetchall(), columns=cols)
    for col in df.columns:  # Snowflake NUMBER(p,s) arrives as Decimal -> make it numeric
        if df[col].dtype == object and df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def run_query(conn, sql: str, params: dict | tuple | None = None) -> pd.DataFrame:
    """Execute a parameterised query (pyformat %(name)s / %s) on an open connection."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return _to_frame(cur)


def query_df(sql: str, params: dict | tuple | None = None, role: str | None = None) -> pd.DataFrame:
    with connection(role) as conn:
        return run_query(conn, sql, params)


def execute(sql: str, params: dict | tuple | None = None, role: str | None = None) -> int:
    """Run a DML statement and return affected row count."""
    with connection(role) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            n = cur.rowcount or 0
        conn.commit()
        return n
