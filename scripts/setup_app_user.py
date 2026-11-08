"""Generate an RSA key pair for the BMTC_STREAMLIT_APP service user and register the public key.

Writes (both git-ignored, never printed):
  secrets/bmtc_app_rsa_key.p8           private key (PEM, unencrypted)
  secrets/streamlit_cloud_secrets.toml  ready to paste into Streamlit Community Cloud > Secrets
Re-running rotates the key.
Run: venv\\Scripts\\python.exe scripts\\setup_app_user.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.snowflake_connection import connection  # noqa: E402

SECRETS = ROOT / "secrets"
SECRETS.mkdir(exist_ok=True)

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption()).decode()
pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                    serialization.PublicFormat.SubjectPublicKeyInfo).decode()
pub_body = "".join(l for l in pub.splitlines() if "-----" not in l)

with connection(role="ACCOUNTADMIN") as conn:
    with conn.cursor() as cur:
        # value is bound, not concatenated
        cur.execute("ALTER USER BMTC_STREAMLIT_APP SET RSA_PUBLIC_KEY = %(k)s", {"k": pub_body})
        cur.execute("DESC USER BMTC_STREAMLIT_APP")
        fp = [r[1] for r in cur.fetchall() if r[0] == "RSA_PUBLIC_KEY_FP"]

(SECRETS / "bmtc_app_rsa_key.p8").write_text(pem, encoding="utf-8")
account = os.getenv("SNOWFLAKE_ACCOUNT", "")
(SECRETS / "streamlit_cloud_secrets.toml").write_text(
    "# Paste into Streamlit Community Cloud > App settings > Secrets. Keep private.\n"
    f'SNOWFLAKE_ACCOUNT = "{account}"\n'
    'SNOWFLAKE_USER = "BMTC_STREAMLIT_APP"\n'
    'SNOWFLAKE_ROLE = "BMTC_APP"\n'
    'SNOWFLAKE_WAREHOUSE = "BMTC_WH"\n'
    'SNOWFLAKE_DATABASE = "BMTC_DW"\n'
    'SNOWFLAKE_SCHEMA = "BUS"\n'
    f'SNOWFLAKE_PRIVATE_KEY = """{pem}"""\n', encoding="utf-8")
print("Public key registered for BMTC_STREAMLIT_APP; fingerprint set:", bool(fp and fp[0]))
print("Wrote secrets/bmtc_app_rsa_key.p8 and secrets/streamlit_cloud_secrets.toml (git-ignored)")
