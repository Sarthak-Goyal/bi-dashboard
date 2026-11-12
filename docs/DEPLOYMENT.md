# Deploying to Railway

The repository ships a single `Dockerfile` that builds the React app and serves it together with the API from one process, so you deploy **one service plus one Postgres database**. A `railway.json` is included (Dockerfile build, `/health` healthcheck, restart on failure).

> **Cost:** hosting providers change their plans and free-trial terms often — check the current terms at <https://railway.com/pricing> before you start. Nothing here depends on a particular plan.

## 1. Push the repo to GitHub

The project must be on GitHub first (see the main README). Make sure `package-lock.json` is committed — the Docker build uses `npm ci`.

## 2. Create the project

1. Sign in at <https://railway.com> with GitHub.
2. **New Project → Deploy from GitHub repo →** choose `bi-dashboard`.
3. Railway reads `railway.json` and builds the `Dockerfile`. The first build takes a few minutes.

## 3. Add Postgres

1. In the project canvas: **+ New → Database → Add PostgreSQL**.
2. Open your **app service → Variables** and add:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — a *reference* to the database service (rename `Postgres` if you named it differently) |
   | `ENVIRONMENT` | `production` |
   | `API_KEY` | a long random string — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

The app accepts Railway's `postgres://` / `postgresql://` URL as-is and waits for the database to accept connections on first boot, so start-up order doesn't matter.

3. Railway redeploys automatically when variables change.

## 4. Make it public

**App service → Settings → Networking → Generate Domain.** You'll get a `*.up.railway.app` URL. The service listens on the `PORT` Railway injects.

## 5. Check it works

1. Open `https://<your-domain>/health` → `{"status":"ok", "database":"postgresql", ...}`.
2. Open the dashboard and go to **Pipeline Log**. On the first run, each pipeline should show **LIVE** with rows loaded. If one shows **SAMPLE**, read its error message in the log — the ABS dataflow key or the NSW crime resource ID may have changed (set `CRIME_RESOURCE_ID` / `ABS_BASE_URL` as variables).
3. Trigger a refresh manually (this is what `API_KEY` protects):

   ```bash
   curl -X POST -H "X-API-Key: <your key>" "https://<your-domain>/api/pipeline/refresh?pipeline=all"
   ```

   The in-app **Refresh All** button will report that it needs an API key — that is intentional; scheduled refreshes run on their own (every 6 hours; labour force hourly).

## 6. Link it from the README

Replace the `Live demo` placeholder near the top of `README.md` with your URL and commit.

## Notes

- **One worker only.** The scheduler and the response cache are in-process; the Docker `CMD` pins `--workers 1`. To scale horizontally, move the cache to Redis and run the scheduler in a separate worker service.
- **SQLite vs Postgres.** Without `DATABASE_URL` the app uses SQLite in `/data`. On Railway that disk is ephemeral unless you attach a volume — Postgres is the better choice for a deployed demo.
- **Secrets.** Never commit `.env`. `API_KEY` lives only in Railway's variables.
- **Running locally in the same shape:** `docker compose up --build` (add `--profile postgres` and `DATABASE_URL=postgresql://bi:bi@db:5432/bi` to include Postgres).

## Other hosts

The same image works anywhere that runs a Docker container and provides a `PORT` and a Postgres `DATABASE_URL` — for example Render (Web Service from Docker + a Postgres instance), Fly.io, or a VPS with `docker compose`. Set the same three variables and use `/health` as the health-check path.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Build fails at `npm ci` | `package-lock.json` isn't committed, or it is out of sync with `package.json` (`npm install` locally, commit the lock file) |
| Healthcheck fails right after deploy | First boot waits for Postgres and starts the pipelines in the background — give it up to ~2 minutes (`healthcheckTimeout` is 120 s) |
| `SAMPLE DATA` banner stays | A live source failed; the Pipeline Log shows the error for each run |
| `connection refused` to the database | `DATABASE_URL` reference variable points at the wrong service name |
| 401 on `/api/pipeline/refresh` | Missing or wrong `X-API-Key` header (expected when `API_KEY` is set) |
