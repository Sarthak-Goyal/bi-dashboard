"""
NSW BI Dashboard — FastAPI backend
Entry point: uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import Base
from app.routers import metrics_router, pipeline_router
from app.pipeline import start_scheduler, stop_scheduler, run_all_pipelines
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("Creating database tables…")
    Base.metadata.create_all(bind=engine)

    logger.info("Running initial ETL pipeline…")
    run_all_pipelines()          # populate DB immediately on first boot

    logger.info("Starting background scheduler…")
    start_scheduler()

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down scheduler…")
    stop_scheduler()


app = FastAPI(
    title="NSW BI Dashboard API",
    description=(
        "Live data pipeline serving labour force, CPI, and crime statistics "
        "sourced from ABS and NSW Open Data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)
app.include_router(pipeline_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nsw-bi-dashboard"}


@app.get("/")
def root():
    return {
        "message": "NSW BI Dashboard API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "summary_kpis": "/api/metrics/summary",
            "unemployment": "/api/metrics/unemployment",
            "cpi": "/api/metrics/cpi",
            "crime": "/api/metrics/crime/by-offence",
            "pipeline_status": "/api/pipeline/status",
            "trigger_refresh": "POST /api/pipeline/refresh",
        },
    }
