"""
Background scheduler — runs all ETL pipelines on startup and then hourly.
Uses APScheduler with SQLAlchemy job store for persistence across restarts.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.pipeline.abs_fetcher import fetch_labour_force, fetch_cpi
from app.pipeline.nsw_fetcher import fetch_nsw_crime

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Australia/Sydney")


def run_all_pipelines() -> None:
    """Execute every ETL pipeline in sequence. Called by scheduler + manual trigger."""
    logger.info(f"[Scheduler] Pipeline run started at {datetime.now(timezone.utc).isoformat()}")
    db: Session = SessionLocal()
    try:
        fetch_labour_force(db)
        fetch_cpi(db)
        fetch_nsw_crime(db)
    finally:
        db.close()
    logger.info("[Scheduler] Pipeline run complete")


def run_labour_force_only() -> None:
    db: Session = SessionLocal()
    try:
        fetch_labour_force(db)
    finally:
        db.close()


def run_cpi_only() -> None:
    db: Session = SessionLocal()
    try:
        fetch_cpi(db)
    finally:
        db.close()


def run_crime_only() -> None:
    db: Session = SessionLocal()
    try:
        fetch_nsw_crime(db)
    finally:
        db.close()


def start_scheduler() -> None:
    """Register jobs and start the background scheduler."""
    # Full refresh every 6 hours
    scheduler.add_job(
        run_all_pipelines,
        trigger=IntervalTrigger(hours=6),
        id="full_pipeline",
        replace_existing=True,
        name="Full ETL Pipeline (all sources)",
    )
    # Labour Force more frequent — ABS updates monthly but we poll hourly for demo
    scheduler.add_job(
        run_labour_force_only,
        trigger=IntervalTrigger(hours=1),
        id="labour_force",
        replace_existing=True,
        name="ABS Labour Force",
    )
    scheduler.start()
    logger.info("[Scheduler] Started — jobs: full pipeline every 6h, labour force every 1h")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
