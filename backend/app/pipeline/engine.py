"""
Generic incremental ETL engine used by every pipeline.

  1. Look up the *watermark* — the latest period already stored from a live source.
  2. Fetch only from (watermark − lookback) onwards, so recent revisions are
     picked up but history is not re-downloaded or re-written.
  3. Validate with the data-quality layer (rows dropped / flagged, load can be rejected).
  4. Upsert: insert new rows, update only values that actually changed.
  5. Write an audit row (PipelineRun) with fetched / inserted / updated / skipped counts.
  If the live source fails and the table is empty, clearly-labelled sample data is seeded.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import PipelineRun
from app.pipeline import common
from app.pipeline.quality import Spec, period_index, record_issues, shift_period, validate_frame
from app.config import get_settings

logger = logging.getLogger(__name__)


class QualityGateError(RuntimeError):
    """Raised when validation rejects an entire load."""


@dataclass
class EtlJob:
    name: str                                   # pipeline_name in the audit log
    label: str                                  # human-readable (for logs)
    source_url: str
    model: Any
    key_fields: tuple[str, ...]
    value_fields: tuple[str, ...]
    watermark_col: Any                          # model column holding period/year
    freq: str                                   # M | Q | A
    default_start: str
    lookback: int
    quality: Spec
    fetch: Callable[[str], pd.DataFrame]        # start_period -> raw DataFrame
    prepare: Callable[[pd.DataFrame], pd.DataFrame]          # raw -> canonical frame to validate
    to_rows: Callable[[Session, pd.DataFrame], list[dict]]   # clean frame -> DB row dicts
    window: Callable[[str], Any]                # start_period -> filter on existing rows
    sample_rows: Callable[[], list[dict]]


def run_etl(db: Session, job: EtlJob) -> PipelineRun:
    wm = common.get_watermark(db, job.model, job.watermark_col)
    start = shift_period(str(wm), job.freq, -job.lookback) if wm is not None else job.default_start
    run = common.start_run(db, job.name, job.source_url, watermark=str(wm) if wm is not None else None)

    try:
        logger.info("[%s] fetching from %s (watermark=%s)", job.label, start, wm)
        raw = job.fetch(start)
        canonical = job.prepare(raw)
        result = validate_frame(canonical, job.quality, get_settings().quality_max_drop_fraction)
        n_issues = record_issues(db, job.name, run.id, result.issues)
        if result.rejected:
            raise QualityGateError(result.reject_reason)

        # Validate everything we were given (more context for outlier/gap checks), but only
        # write rows inside the incremental window — some sources (CKAN) ignore the start period.
        floor = period_index(start, job.freq)
        clean = result.df
        if floor is not None:
            keep = clean["period"].map(lambda p: (period_index(p, job.freq) or 0) >= floor)
            clean = clean[keep]
        rows = job.to_rows(db, clean)
        common.purge_synthetic(db, job.model)
        ins, upd, _same = common.upsert(
            db, job.model, rows, job.key_fields, job.value_fields, window_filter=job.window(start),
        )
        logger.info("[%s] ✓ live — fetched=%d inserted=%d updated=%d skipped=%d issues=%d",
                    job.label, len(raw), ins, upd, result.dropped, n_issues)
        return common.finish_run(db, run, status="success", mode="live", fetched=len(raw),
                                 inserted=ins, updated=upd, skipped=result.dropped, quality_issues=n_issues)

    except Exception as exc:                     # noqa: BLE001 — every failure is logged + audited
        db.rollback()
        msg = f"{type(exc).__name__}: {exc}"[:500]
        logger.warning("[%s] ✗ %s", job.label, msg)
        mode: Optional[str] = None
        if not common.has_rows(db, job.model):
            logger.warning("[%s] no stored data — seeding clearly-labelled SAMPLE data", job.label)
            sample = job.sample_rows()
            common.upsert(db, job.model, sample, job.key_fields, job.value_fields, synthetic=True)
            mode = "sample"
        else:
            existing_synth = db.query(job.model.id).filter(job.model.is_synthetic.is_(True)).first()
            mode = "sample" if existing_synth else "live"   # keep serving what we have
        return common.finish_run(db, run, status="failed", mode=mode, error=msg)
