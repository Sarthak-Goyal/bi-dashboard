"""
Background scheduler — runs the ETL pipelines on startup and on a schedule.
Intervals come from settings (FULL_REFRESH_HOURS, LABOUR_REFRESH_HOURS).
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.pipeline.abs_fetcher import fetch_building_approvals, fetch_cpi, fetch_labour_force
from app.pipeline.nsw_fetcher import fetch_nsw_crime

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Australia/Sydney")
_run_lock = threading.Lock()          # one pipeline batch at a time


def _run(fetchers: list[Callable]) -> None:
    if not _run_lock.acquire(blocking=False):
        logger.info("[Scheduler] A run is already in progress — skipping")
        return
    try:
        logger.info("[Scheduler] Run started at %s", datetime.now(timezone.utc).isoformat())
        for fetch in fetchers:
            db = SessionLocal()
            try:
                fetch(db)                      # failures are handled + audited inside the engine
            except Exception:                  # noqa: BLE001 — never let one pipeline stop the others
                logger.exception("[Scheduler] Unhandled error in %s", getattr(fetch, "__name__", fetch))
            finally:
                db.close()
        logger.info("[Scheduler] Run complete")
    finally:
        _run_lock.release()


def run_all_pipelines() -> None:
    _run([fetch_labour_force, fetch_cpi, fetch_building_approvals, fetch_nsw_crime])


def run_labour_force_only() -> None:
    _run([fetch_labour_force])


def run_cpi_only() -> None:
    _run([fetch_cpi])


def run_building_only() -> None:
    _run([fetch_building_approvals])


def run_crime_only() -> None:
    _run([fetch_nsw_crime])


def start_scheduler() -> None:
    s = get_settings()
    scheduler.add_job(run_all_pipelines, IntervalTrigger(hours=s.full_refresh_hours),
                      id="full_pipeline", replace_existing=True, name="Full ETL pipeline")
    scheduler.add_job(run_labour_force_only, IntervalTrigger(hours=s.labour_refresh_hours),
                      id="labour_force", replace_existing=True, name="ABS Labour Force")
    scheduler.start()
    logger.info("[Scheduler] Started — full refresh every %dh, labour force every %dh",
                s.full_refresh_hours, s.labour_refresh_hours)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
