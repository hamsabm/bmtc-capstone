# Manual steps

Everything else is built, deployed and tested (see `TEST_RESULTS.md`).

## 1. Save the Power BI dashboard as .pbix

The dashboard is built as a Power BI Project (`powerbi/BMTC_Dashboard.pbip`): 8 tables, 15 measures, 2 relationships,
2 pages and 18 visuals. It has been refreshed against Snowflake in Power BI Desktop.
To produce the submission file: in Power BI Desktop choose **File → Save As**, set **Save as type** to
**Power BI file (\*.pbix)**, and save as `powerbi/BMTC_Dashboard.pbix`. Then take a screenshot of each page for the report.

If Power BI asks for Snowflake credentials, use your own Snowflake user. The demo users have no password.

## 2. Snowflake trial-account limitations (explain in the demo; nothing to fix)

- **Data sharing consumer:** a second Snowflake account is needed to consume `BMTC_ROUTE_PERFORMANCE_SHARE`.
- **Snowpipe auto-ingest:** an external S3/Azure/GCS stage with event notifications is needed. The internal-stage
  pipe works with `ALTER PIPE ... REFRESH`.
- **Default secondary roles = ALL** on this account: run `USE SECONDARY ROLES NONE` before demonstrating role isolation.

## Deployment (done)

The app is live at https://bmtc-capstone-khikgndfeza5wceasi6uzc.streamlit.app. It uses the least-privilege key-pair user `BMTC_STREAMLIT_APP` (role `BMTC_APP`),
and its secrets are stored only in Streamlit Cloud (local copy: `secrets/`, git-ignored).
To rotate the key, run `scripts/setup_app_user.py` and paste the new `secrets/streamlit_cloud_secrets.toml` into Streamlit
Cloud → Settings → Secrets. To take the site offline, run `ALTER USER BMTC_STREAMLIT_APP SET DISABLED = TRUE;`
