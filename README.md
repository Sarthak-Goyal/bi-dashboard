# 📊 NSW BI Dashboard — Incremental Data Pipeline

[![CI](https://github.com/Sarthak-Goyal/bi-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Sarthak-Goyal/bi-dashboard/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![Postgres](https://img.shields.io/badge/SQLite%20%7C%20Postgres-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)

A full-stack business-intelligence dashboard built around a **production-style ETL pipeline**: four public data sources from the **Australian Bureau of Statistics (ABS)** and **NSW Open Data** are loaded incrementally, validated by a data-quality layer, joined across sources, and served through a cached, paginated REST API to a responsive React dashboard.

> **Live demo:** _add your Railway URL here after deploying — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)_

![Overview](docs/screenshots/overview.png)

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/crime-map.png" alt="Choropleth map of NSW local government areas"><br><sub><b>Choropleth</b> of all 129 NSW council areas — rate per 100k or raw incidents, NSW or Greater Sydney view.</sub></td>
    <td width="50%"><img src="docs/screenshots/housing-join.png" alt="Building approvals joined with unemployment and CPI"><br><sub><b>Multi-source join</b> — building approvals ⨝ unemployment ⟕ CPI, joined on period.</sub></td>
  </tr>
</table>

> The data screenshots above were captured with the app running **without internet access**, so it is displaying clearly-labelled *sample* data (note the amber banner and `SAMPLE DATA` badge). The dashboard never presents generated numbers as real statistics.

---

## What this project demonstrates

| Area | What's implemented |
|---|---|
| **Data engineering** | 4 sources · multi-source join · **incremental loads with a watermark** · upserts that apply revisions · **data-quality validation layer** · audit log for every run |
| **Backend** | FastAPI · **TTL response cache** (invalidated on every load) · **pagination** · **Pydantic-validated SDMX parsing** · **API-key protected write endpoint** · `pydantic-settings` configuration |
| **Database** | SQLite out of the box, **Postgres by changing one environment variable** (`DATABASE_URL`) — the full test suite runs against both in CI |
| **Frontend** | **Responsive** layout (collapsible drawer, stacking charts) · **date-range pickers** · **skeleton loading** · **choropleth map** · **CSV export** on every chart · accessible (keyboard, focus rings, reduced motion, ARIA) |
| **DevOps** | **GitHub Actions CI** (tests on SQLite + Postgres, frontend build, Docker build + smoke test) · single **non-root Docker image** · healthcheck · Railway config |

---

## Architecture

```mermaid
flowchart LR
    subgraph Sources
        A1[ABS Labour Force<br/>SDMX · monthly]
        A2[ABS CPI<br/>SDMX · quarterly]
        A3[ABS Building Approvals<br/>SDMX · monthly]
        A4[NSW Open Data<br/>CKAN · annual crime]
    end

    subgraph ETL["ETL engine (APScheduler)"]
        direction TB
        W[Watermark lookup<br/>fetch only new periods] --> V[Schema validation<br/>SDMX → Pydantic]
        V --> Q[Data-quality layer<br/>range · duplicates · outliers · gaps]
        Q --> U[Upsert<br/>insert new · update revised]
    end

    DB[(SQLite / Postgres)]
    API[FastAPI<br/>cache · pagination · API key]
    UI[React dashboard<br/>Recharts · D3 map]

    A1 & A2 & A3 & A4 --> W
    U --> DB --> API --> UI
    Q -. issues & audit .-> DB
```

### How an incremental load works

1. **Watermark** — the engine asks the database for the latest period already stored *from a live source*.
2. **Fetch from `watermark − lookback`** — a few recent periods are re-requested so ABS revisions are picked up, but history is never re-downloaded.
3. **Validate** — the response is checked against Pydantic models (so a changed ABS response shape produces one clear error), then run through the quality checks below.
4. **Quality gate** — if more than 20 % of rows fail validation the whole load is rejected and existing data is left untouched.
5. **Upsert** — new rows are inserted, changed values updated, identical rows left alone (so `updated_at` means something).
6. **Audit** — a `pipeline_runs` row records the watermark, rows fetched / inserted / revised / dropped and the number of quality issues.

Running the same load twice changes nothing — this is covered by tests.

### Data-quality layer

| Check | Action | Example |
|---|---|---|
| Schema | reject load | response is missing columns, empty, or not SDMX |
| Duplicates | drop (keep last) | the feed repeats a period |
| Plausible range | **drop** row, log `error` | unemployment rate of 250 % |
| Outliers (robust z-score) | **keep**, log `warning` | 31 % in a series that sits around 3.8 % |
| Missing periods | log `warning` | no data for 2025-03 |

Findings are stored in `data_quality_issues` and shown on the **Pipeline Log** page.

### Honest data provenance

Every row carries an `is_synthetic` flag. If a live source can't be reached **and nothing is stored yet**, the pipeline seeds deterministic sample data so the dashboard still renders — and then:

- the API reports `data_mode: live | sample | mixed`,
- the UI shows a banner and a `SAMPLE DATA` badge,
- sample rows are **deleted automatically** the first time live data arrives, so the two are never mixed.

---

## Quick start

**Requirements:** Python **3.12** (3.13+ is not yet supported by some pinned packages) · Node.js 18+ (20 recommended) · Git

```bash
git clone https://github.com/Sarthak-Goyal/bi-dashboard.git
cd bi-dashboard
```

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate            # macOS / Linux
source venv/Scripts/activate        # Windows (Git Bash)
pip install -r requirements.txt

cp .env.example .env                # optional — every setting has a default
uvicorn app.main:app --reload       # API on :8000, Swagger at /docs
```

On first start the pipelines run in a background thread, so the server is available immediately; open the Pipeline Log to watch them.

**Frontend** (second terminal)

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173  (proxies /api to :8000)
```

Each page has its own URL (`#overview`, `#labour`, `#cpi`, `#housing`, `#crime`, `#pipeline`).

### Try the data-quality layer offline

`backend/scripts/demo_upstream.py` is a local stand-in for the ABS and NSW APIs that serves *generated* data with deliberate problems (a missing month, an outlier, an impossible value, rows from other states):

```bash
# terminal 1
cd backend && python scripts/demo_upstream.py

# terminal 2 (Git Bash / macOS / Linux)
cd backend
ABS_BASE_URL=http://127.0.0.1:9000/data CKAN_BASE_URL=http://127.0.0.1:9000/ckan \
RUN_PIPELINES_ON_STARTUP=sync uvicorn app.main:app
```

Open the **Pipeline Log** to see dropped rows and warnings. Then `curl http://127.0.0.1:9000/__advance` and click **Refresh All** (or `POST /api/pipeline/refresh`): only the new month is inserted and one value is revised.

![Pipeline log with data-quality issues](docs/screenshots/pipeline-quality.png)

<sub>Captured from the demo script above — generated numbers, shown only to illustrate the pipeline log and quality panel.</sub>

---

## Configuration

All settings are optional and read from environment variables or `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | _(empty → SQLite)_ | e.g. `postgresql://user:pass@host:5432/db`. `postgres://` URLs from hosting providers are accepted |
| `DATA_DIR` | `backend/data` | Where the SQLite file lives |
| `API_KEY` | _(empty → open)_ | If set, `POST /api/pipeline/refresh` requires an `X-API-Key` header |
| `ENVIRONMENT` | `development` | `production` logs a warning if `API_KEY` is unset |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed browser origins |
| `RUN_PIPELINES_ON_STARTUP` | `background` | `background` · `sync` · `off` |
| `ENABLE_SCHEDULER` | `true` | Scheduled refreshes |
| `FULL_REFRESH_HOURS` / `LABOUR_REFRESH_HOURS` | `6` / `1` | Schedule intervals |
| `CACHE_TTL_SECONDS` | `60` | API response cache lifetime |
| `STATIC_DIR` | _(empty)_ | Serve a built frontend from the API process (used by Docker) |
| `CRIME_RESOURCE_ID`, `ABS_BASE_URL`, `CKAN_BASE_URL` | built-in | Override if a publisher moves its dataset |

### Using Postgres

```bash
pip install -r requirements.txt           # includes psycopg2-binary
DATABASE_URL=postgresql://user:pass@localhost:5432/bi uvicorn app.main:app
```

No code changes — tables are created on startup, and the app waits for the database to become ready. If an older v1 SQLite file is found it is rebuilt automatically (the data is re-fetchable).

---

## Data sources — and what to verify

| Dataset | Source | Frequency |
|---|---|---|
| Unemployment & participation rate (NSW, Australia) | ABS Labour Force — dataflow `LF` | Monthly |
| CPI, Sydney, all groups | ABS CPI — dataflow `CPI` | Quarterly |
| Dwelling approvals, NSW | ABS Building Approvals — dataflow `BA_GCCSA` | Monthly |
| Recorded crime by LGA & offence | NSW Open Data (BOCSAR) via CKAN | Annual |

Public statistical APIs change over time (dataflow keys, column names, resource IDs). The pipeline is built to **fail visibly instead of silently**: if a source can't be read, the run is recorded as `failed` with the reason, previously stored data is kept, and the UI says so.

**After deploying, open the Pipeline Log and check each source shows `LIVE`.** In particular, the Building Approvals pipeline selects its series by dimension *labels* rather than a fixed key, and the NSW crime resource ID is configurable (`CRIME_RESOURCE_ID`) — adjust them if a source shows `SAMPLE`.

---

## API

Interactive docs at `/docs`.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/metrics/summary` | KPI cards + `data_mode` — **cached** (`X-Cache: HIT/MISS`) |
| GET | `/api/metrics/data-mode` | `live` / `sample` / `mixed` per dataset |
| GET | `/api/metrics/unemployment/compare?months=24` | `months=0` → all history |
| GET | `/api/metrics/cpi?quarters=20` | `quarters=0` → all history |
| GET | `/api/metrics/housing-labour?months=36` | **Join** of approvals, unemployment, CPI + correlation |
| GET | `/api/metrics/crime/by-offence` · `/crime/offences` · `/crime/top-lgas` | |
| GET | `/api/metrics/crime/trend?offence=Theft&years=5` | |
| GET | `/api/metrics/crime/by-lga?offence=All` | Feeds the choropleth |
| GET | `/api/metrics/records/{dataset}?page=1&page_size=50` | **Paginated** raw rows |
| GET | `/api/pipeline/status` | Latest run per pipeline |
| GET | `/api/pipeline/history?page=1&page_size=20` | **Paginated** audit log |
| GET | `/api/pipeline/quality?severity=error&page=1` | **Paginated** data-quality issues |
| GET | `/api/pipeline/cache` | Cache hit-rate |
| POST | `/api/pipeline/refresh?pipeline=all` | 🔒 requires `X-API-Key` when `API_KEY` is set |
| GET | `/health` | Liveness + DB dialect + data mode |

```bash
curl -X POST -H "X-API-Key: $API_KEY" "http://localhost:8000/api/pipeline/refresh?pipeline=abs_cpi"
```

> The frontend can send the key via `VITE_API_KEY`, but anything in a browser bundle is public — the header demonstrates the pattern for protecting a write endpoint; it is not a substitute for per-user authentication.

---

## Docker

One image builds the React app and serves it together with the API (one process, one port), running as a **non-root user** with a healthcheck.

```bash
docker compose up --build                     # http://localhost:8000  (SQLite in a volume)

# with Postgres
DATABASE_URL=postgresql://bi:bi@db:5432/bi docker compose --profile postgres up --build
```

## Deploying

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for a step-by-step Railway guide (the repo includes a `railway.json`).

---

## Testing & CI

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q                                                              # SQLite
TEST_DATABASE_URL=postgresql://user:pass@localhost/bitest python -m pytest -q    # Postgres
```

44 tests cover SDMX schema validation, every quality check, incremental loads (idempotency, watermark windows, revisions, quality-gate rejection, schema-change handling), CPI year-on-year maths across incremental windows, building-approvals label filtering, CKAN column mapping, the API (cache, pagination, range parameters, joins, auth) and single-container static serving including path-traversal protection.

GitHub Actions (`.github/workflows/ci.yml`) runs on every push: backend tests on **SQLite and Postgres**, the frontend production build, and a Docker image build that starts the container and checks `/health`, the served UI, and that it isn't running as root.

---

## Project structure

```
bi-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py                  FastAPI app · lifespan · static serving
│   │   ├── config.py                pydantic-settings (env-driven)
│   │   ├── database.py              SQLite / Postgres engine, startup wait
│   │   ├── models.py                tables + provenance columns
│   │   ├── cache.py  security.py    TTL cache · API-key dependency
│   │   ├── routers/                 metrics.py · pipeline.py
│   │   ├── pipeline/
│   │   │   ├── engine.py            generic incremental ETL engine
│   │   │   ├── sdmx.py              Pydantic-validated SDMX-JSON parser
│   │   │   ├── quality.py           data-quality validation layer
│   │   │   ├── abs_fetcher.py       Labour Force · CPI · Building Approvals
│   │   │   ├── nsw_fetcher.py       NSW Open Data (CKAN)
│   │   │   ├── sample_data.py       labelled synthetic fallback
│   │   │   └── scheduler.py         APScheduler jobs
│   │   └── data/lga_names.json
│   ├── tests/                       44 tests
│   └── scripts/demo_upstream.py     offline ABS/NSW stand-in with injected bad data
├── frontend/
│   ├── public/geo/nsw_lga.geojson   129 LGA boundaries (CC BY 4.0)
│   └── src/  components/ hooks/ utils/
├── docs/                            deployment guide + screenshots
├── Dockerfile  docker-compose.yml  railway.json
└── .github/workflows/ci.yml
```

---

## Data sources & licences

- **ABS data** — © Commonwealth of Australia, licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Accessed via the [ABS Data API](https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis).
- **NSW Open Data** — © State of New South Wales, licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Crime data from [BOCSAR](https://www.bocsar.nsw.gov.au) via [data.nsw.gov.au](https://data.nsw.gov.au).
- **Council boundaries** — ABS Australian Statistical Geography Standard (ASGS) Edition 3, LGA 2024, © Commonwealth of Australia, CC BY 4.0. Obtained via the [`nswgeo`](https://github.com/cidm-ph/nswgeo) R package and simplified for web display. See [`frontend/public/geo/ATTRIBUTION.txt`](frontend/public/geo/ATTRIBUTION.txt).

---

## 👤 Author

**Sarthak** — Master of Information Technology, University of Technology Sydney  
Portfolio: [github.com/Sarthak-Goyal](https://github.com/Sarthak-Goyal) · Sydney, NSW 🇦🇺
