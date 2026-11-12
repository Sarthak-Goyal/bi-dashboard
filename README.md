# 📊 NSW BI Dashboard — Live Data Pipeline

> A full-stack business intelligence dashboard powered by a live ETL pipeline, sourcing real public data from the **Australian Bureau of Statistics (ABS)** and **NSW Open Data** portal.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)

---

## 🎯 Overview

This project demonstrates a production-style **data engineering pipeline** combined with an interactive **visualisation layer**. It targets three real-world datasets relevant to the NSW economy:

| Data Source | Dataset | Frequency |
|---|---|---|
| ABS SDMX API | Labour Force — NSW unemployment & participation rate | Monthly |
| ABS SDMX API | Consumer Price Index — Sydney, all groups | Quarterly |
| NSW Open Data (CKAN) | BOCSAR Recorded Crime Statistics by LGA | Annual |

The backend pipeline **automatically refreshes** on a schedule, stores results in SQLite, and exposes a REST API consumed by the React frontend in real time.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Sources                             │
│  ┌───────────────────┐   ┌───────────────────────────────────┐  │
│  │  ABS SDMX API     │   │  NSW Open Data (CKAN API)         │  │
│  │  api.data.abs.gov │   │  data.nsw.gov.au                  │  │
│  └────────┬──────────┘   └──────────────┬────────────────────┘  │
└───────────┼──────────────────────────────┼────────────────────── ┘
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                                                                 │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │  Fetchers   │──▶│ Transformers │──▶│  SQLite (SQLAlch.) │   │
│  │  httpx      │   │  pandas      │   │  /data/dashboard   │   │
│  └─────────────┘   └──────────────┘   └────────────────────┘   │
│                                                ▲                │
│  ┌─────────────────────────────────────────────┤                │
│  │  APScheduler (hourly / 6-hourly jobs)        │               │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
│  REST API   /api/metrics/*   /api/pipeline/*                    │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP / JSON
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                         │
│                                                                 │
│  KPI Cards  │  Line/Bar Charts (Recharts)  │  Pipeline Log      │
│                                                                 │
│  usePolling() hook — auto-refreshes every 30s                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- **Live ETL pipeline** — fetches, validates, and stores data from two government APIs
- **Automatic fallback** — if an API is unavailable, realistic mock data keeps the dashboard populated
- **Pipeline audit log** — every run is recorded with status, record counts, duration, and errors
- **Manual refresh** — trigger any pipeline from the UI without restarting the server
- **NSW vs AUS comparison** — unemployment rate side-by-side with a "full employment" reference line
- **RBA target band** — CPI chart shows the 2–3% Reserve Bank target zone
- **Crime trend drill-down** — switch between offence categories, view top-5 LGAs over time
- **APScheduler** — runs Labour Force hourly, full pipeline every 6 hours
- **Docker Compose** — one command to run backend + frontend + nginx

---

## 🚀 Quick Start

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/nsw-bi-dashboard.git
cd nsw-bi-dashboard

docker compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API (Swagger) | http://localhost:8000/docs |

### Option B — Local development

**Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

mkdir -p /data                    # or set DATABASE_URL in .env
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

> The Vite dev server proxies `/api` → `localhost:8000` automatically.

---

## 📡 API Reference

### Metrics

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/metrics/summary` | Four headline KPI values |
| GET | `/api/metrics/unemployment?region=NSW&months=36` | Monthly unemployment time series |
| GET | `/api/metrics/unemployment/compare` | NSW vs AUS, last 24 months |
| GET | `/api/metrics/cpi?quarters=20` | CPI index + annual % change |
| GET | `/api/metrics/crime/by-offence?year=2023` | Total incidents by offence category |
| GET | `/api/metrics/crime/trend?offence=Theft` | Year-on-year trend, top LGAs |
| GET | `/api/metrics/crime/top-lgas` | Top LGAs by total incidents |

### Pipeline

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/pipeline/status` | Latest run status for each pipeline |
| GET | `/api/pipeline/history?limit=20` | Paginated run history |
| POST | `/api/pipeline/refresh?pipeline=all` | Trigger a manual run |

Full interactive docs at `/docs` (Swagger UI) and `/redoc`.

---

## 🗄️ Data Model

```sql
-- ABS Labour Force
labour_force (id, period, region, metric, value, adjustment, unit, created_at)

-- ABS CPI
cpi (id, period, region, series, index_value, pct_change_annual, created_at)

-- NSW Crime
nsw_crime (id, year, lga_name, offence_category, incidents_recorded, rate_per_100k, created_at)

-- ETL audit log
pipeline_runs (id, pipeline_name, status, records_fetched, records_inserted,
               started_at, completed_at, error_message, source_url)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Data fetch | `httpx` (async-capable) | ABS returns SDMX-JSON; httpx handles timeouts cleanly |
| Data transform | `pandas` | DataFrame pivot for SDMX series → tidy rows |
| ORM / DB | `SQLAlchemy 2` + SQLite | Zero-setup persistence; swap to Postgres via `DATABASE_URL` |
| Scheduling | `APScheduler` | Lightweight cron-style jobs inside the FastAPI process |
| API framework | `FastAPI` | Auto-generated OpenAPI docs; Pydantic validation |
| Charts | `Recharts` | Composable, responsive; native SVG for crisp rendering |
| Build | `Vite` | Fast HMR in dev; optimised production bundle |
| Container | Docker + nginx | Multi-stage build keeps frontend image ~25 MB |

---

## 📁 Project Structure

```
nsw-bi-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan (DB init, scheduler)
│   │   ├── database.py          # SQLAlchemy engine + session factory
│   │   ├── models.py            # ORM table definitions
│   │   ├── pipeline/
│   │   │   ├── abs_fetcher.py   # ABS SDMX API → SQLite (Labour Force + CPI)
│   │   │   ├── nsw_fetcher.py   # NSW Open Data CKAN API → SQLite (Crime)
│   │   │   └── scheduler.py     # APScheduler job registration
│   │   └── routers/
│   │       ├── metrics.py       # /api/metrics/* endpoints
│   │       └── pipeline.py      # /api/pipeline/* endpoints
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root layout + page routing
│   │   ├── index.css            # Design tokens + global styles
│   │   ├── components/
│   │   │   ├── PipelineStatus.jsx  # Animated ETL flow bar
│   │   │   ├── KPICard.jsx         # Headline metric card
│   │   │   ├── UnemploymentChart.jsx
│   │   │   ├── CPIChart.jsx
│   │   │   ├── CrimeCharts.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── PipelineLog.jsx
│   │   ├── hooks/useMetrics.js  # usePolling + useOnce data hooks
│   │   └── utils/api.js         # Typed API client
│   ├── package.json
│   └── vite.config.js
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
└── docker-compose.yml
```

---

## 🔧 Configuration

Create `backend/.env` to override defaults:

```env
# Database (defaults to /data/dashboard.db)
DATABASE_URL=sqlite:////data/dashboard.db

# Scheduler intervals (hours)
FULL_PIPELINE_INTERVAL_HOURS=6
LABOUR_FORCE_INTERVAL_HOURS=1
```

---

## 📌 Data Sources & Licences

- **ABS Data** — © Commonwealth of Australia. Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
  Accessed via the [ABS SDMX RESTful API](https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis).
- **NSW Open Data** — © State of New South Wales. Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
  Crime data sourced from [BOCSAR](https://www.bocsar.nsw.gov.au) via [data.nsw.gov.au](https://data.nsw.gov.au).

---

## 👤 Author

**Sarthak** — Master of Information Technology, University of Technology Sydney  
Portfolio: [github.com/YOUR_USERNAME](https://github.com/YOUR_USERNAME) · Sydney, NSW 🇦🇺
