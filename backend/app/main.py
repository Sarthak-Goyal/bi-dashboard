"""
NSW BI Dashboard — FastAPI backend
Run locally:  uvicorn app.main:app --reload
"""

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import cache
from app.config import get_settings
from app.database import DIALECT, SessionLocal, init_db
from app.pipeline import run_all_pipelines, start_scheduler, stop_scheduler
from app.routers import metrics_router, pipeline_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Environment=%s  database=%s", settings.environment, DIALECT)
    init_db()

    if not settings.api_key:
        level = logging.WARNING if settings.is_production else logging.INFO
        logger.log(level, "API_KEY is not set — POST /api/pipeline/refresh is open to anyone")

    mode = settings.run_pipelines_on_startup.lower()
    if mode == "sync":
        run_all_pipelines()
    elif mode == "background":
        # Don't block startup (and platform health checks) on slow upstream APIs
        threading.Thread(target=run_all_pipelines, name="initial-etl", daemon=True).start()

    if settings.enable_scheduler:
        start_scheduler()

    yield

    stop_scheduler()


app = FastAPI(
    title="NSW BI Dashboard API",
    description=(
        "Incremental ETL pipelines (ABS Labour Force, CPI, Building Approvals; NSW Open Data crime) "
        "with a data-quality layer, served through a cached, paginated REST API."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Cache"],
)

app.include_router(metrics_router)
app.include_router(pipeline_router)


@app.get("/health", tags=["system"])
def health():
    from app.routers.metrics import data_mode
    db = SessionLocal()
    try:
        mode = data_mode(db)["overall"]
    finally:
        db.close()
    return {"status": "ok", "service": "nsw-bi-dashboard", "version": app.version,
            "database": DIALECT, "data_mode": mode, "cache": cache.stats()}


# ── Serve the built React app (single-container deployments) ─────────────────

STATIC_DIR = Path(settings.static_dir).resolve() if settings.static_dir else None

if STATIC_DIR and (STATIC_DIR / "index.html").exists():
    logger.info("Serving frontend from %s", STATIC_DIR)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi")):
            raise HTTPException(404, "Not found")
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR in candidate.parents:   # blocks ../ traversal
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/", tags=["system"])
    def root():
        return {
            "message": "NSW BI Dashboard API", "docs": "/docs", "health": "/health",
            "endpoints": {
                "summary_kpis": "/api/metrics/summary",
                "unemployment": "/api/metrics/unemployment/compare",
                "cpi": "/api/metrics/cpi",
                "housing_labour_join": "/api/metrics/housing-labour",
                "crime_by_lga": "/api/metrics/crime/by-lga",
                "pipeline_status": "/api/pipeline/status",
                "data_quality": "/api/pipeline/quality",
                "trigger_refresh": "POST /api/pipeline/refresh  (X-API-Key)",
            },
        }
