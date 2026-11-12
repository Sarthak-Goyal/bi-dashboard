"""Shared pipeline plumbing: run lifecycle, HTTP, incremental upsert, sample-data handling."""

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import cache
from app.config import get_settings
from app.models import PipelineRun

logger = logging.getLogger(__name__)

ABS_HEADERS = {"Accept": "application/vnd.sdmx.data+json;version=1.0"}


# ── HTTP ─────────────────────────────────────────────────────────────────────

def http_get_json(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None) -> Any:
    """Single place for outbound HTTP so tests can stub it."""
    with httpx.Client(timeout=get_settings().http_timeout, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ── Run lifecycle ────────────────────────────────────────────────────────────

def start_run(db: Session, name: str, url: str, watermark: Optional[str] = None) -> PipelineRun:
    run = PipelineRun(pipeline_name=name, status="running", source_url=url, watermark=watermark)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_run(
    db: Session, run: PipelineRun, *, status: str, mode: Optional[str] = None,
    fetched: int = 0, inserted: int = 0, updated: int = 0, skipped: int = 0,
    quality_issues: int = 0, error: Optional[str] = None,
) -> PipelineRun:
    run.status = status
    run.mode = mode
    run.records_fetched = fetched
    run.records_inserted = inserted
    run.records_updated = updated
    run.records_skipped = skipped
    run.quality_issues = quality_issues
    run.error_message = error
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    cache.clear()          # new data → drop cached API responses
    return run


# ── Incremental loading ──────────────────────────────────────────────────────

def get_watermark(db: Session, model, column) -> Optional[Any]:
    """Latest period/year already stored from a *live* source (sample rows ignored)."""
    return db.query(func.max(column)).filter(model.is_synthetic.is_(False)).scalar()


def purge_synthetic(db: Session, model) -> int:
    """Remove sample rows once real data arrives, so the two are never mixed."""
    n = db.query(model).filter(model.is_synthetic.is_(True)).delete(synchronize_session=False)
    if n:
        db.commit()
        logger.info("Removed %d sample rows from %s", n, model.__tablename__)
    return n


def has_rows(db: Session, model) -> bool:
    return db.query(model.id).first() is not None


def upsert(
    db: Session, model, rows: Iterable[dict], key_fields: tuple[str, ...],
    value_fields: tuple[str, ...], window_filter=None, synthetic: bool = False,
) -> tuple[int, int, int]:
    """
    Insert new rows, update changed ones, leave identical ones untouched.
    Returns (inserted, updated, unchanged). `window_filter` is an optional SQLAlchemy
    expression limiting which existing rows are loaded for comparison.
    """
    rows = list(rows)
    if not rows:
        return 0, 0, 0

    q = db.query(model)
    if window_filter is not None:
        q = q.filter(window_filter)
    existing = {tuple(getattr(r, k) for k in key_fields): r for r in q.all()}

    inserted = updated = unchanged = 0
    for row in rows:
        key = tuple(row[k] for k in key_fields)
        current = existing.get(key)
        if current is None:
            db.add(model(**row, is_synthetic=synthetic))
            inserted += 1
            continue
        changed = False
        for f in value_fields:
            new, old = row.get(f), getattr(current, f)
            if new is None and old is None:
                continue
            if new is None or old is None or (
                abs(float(new) - float(old)) > 1e-9 if isinstance(new, (int, float)) else new != old
            ):
                setattr(current, f, new)
                changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1
    db.commit()
    return inserted, updated, unchanged
