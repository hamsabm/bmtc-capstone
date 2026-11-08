# Manual steps

Only the items below need you. Everything else is built and tested (see `TEST_RESULTS.md`).

## 1. Create the Power BI dashboard (.pbix)

No `.pbix` exists yet. Power BI Desktop is a GUI application.
Follow `powerbi/POWERBI_SETUP.md`: connect with Get data → Snowflake, load the listed views, and build the visuals.
All views and queries already exist in `BMTC_DW` and were verified.

For your login, use your own Snowflake user. With role `BMTC_VIEWER`, run `USE SECONDARY ROLES NONE` first if you want
to see that the viewer role is restricted. You can also give the demo account a password in Snowsight:
`ALTER USER BMTC_POWERBI_VIEWER SET PASSWORD = '<your choice>';`

## 2. Unavoidable Snowflake trial-account limitations (explain them in your demo; nothing to fix)

- **Data sharing consumer:** a second Snowflake account is needed to consume `BMTC_ROUTE_PERFORMANCE_SHARE`.
- **Snowpipe auto-ingest:** an external S3/Azure/GCS stage with event notifications is needed. The internal-stage
  pipe works with `ALTER PIPE ... REFRESH`.
- **Default secondary roles = ALL** on this account: run `USE SECONDARY ROLES NONE` before demonstrating role isolation.

## 3. Public deployment (optional; it cannot be automated from here)

The app currently runs **locally only** (http://localhost:8501). Publishing it requires your GitHub and
Streamlit Community Cloud logins.

> Do **not** deploy with your ACCOUNTADMIN password. The deployment uses the least-privilege key-pair
> service user `BMTC_STREAMLIT_APP` (role `BMTC_APP`). It is **already created and tested**.
> Its secrets are in `secrets\streamlit_cloud_secrets.toml` (git-ignored; keep private).
> Running `scripts\setup_app_user.py` again rotates the key.

```powershell
# push the code to a PRIVATE GitHub repo (.env, secrets\ and keys are git-ignored)
git init
git add .
git status        # confirm .env, secrets\ and venv\ are NOT listed
git commit -m "BMTC capstone"
git branch -M main
# create an EMPTY private repo named bmtc-capstone at https://github.com/new (no README), then:
git remote add origin https://github.com/<your-github-username>/bmtc-capstone.git
git push -u origin main
```

d) Go to https://share.streamlit.io → **Create app** → choose the repo, branch `main`, main file `app.py`.
Open **Advanced settings**, choose Python 3.12, and paste the contents of `secrets\streamlit_cloud_secrets.toml`
into **Secrets**. Click **Deploy**. The URL will look like `https://<your-app-name>.streamlit.app`.

To stop public access later: delete the app in Streamlit Cloud, or run
`ALTER USER BMTC_STREAMLIT_APP SET DISABLED = TRUE;`
