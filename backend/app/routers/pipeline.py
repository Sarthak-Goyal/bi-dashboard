"""
/api/pipeline/* — pipeline status, audit history, data-quality issues, manual trigger.
"""

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app import cache
from app.database import get_db
from app.models import DataQualityIssue, PipelineRun
from app.pipeline.scheduler import (
    run_all_pipelines, run_building_only, run_cpi_only, run_crime_only, run_labour_force_only,
)
from app.security import require_api_key

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

PIPELINE_NAMES = {
    "abs_labour_force": "ABS Labour Force",
    "abs_cpi": "ABS Consumer Price Index",
    "abs_building_approvals": "ABS Building Approvals",
    "nsw_crime": "NSW Crime Statistics",
}

HANDLERS = {
    "all": run_all_pipelines,
    "abs_labour_force": run_labour_force_only,
    "abs_cpi": run_cpi_only,
    "abs_building_approvals": run_building_only,
    "nsw_crime": run_crime_only,
}


@router.get("/status")
def get_pipeline_status(db: Session = Depends(get_db)):
    """Latest run for each pipeline plus aggregate health."""
    statuses = []
    for name, display in PIPELINE_NAMES.items():
        latest = (db.query(PipelineRun).filter(PipelineRun.pipeline_name == name)
                  .order_by(desc(PipelineRun.started_at), desc(PipelineRun.id)).first())
        total = db.query(func.count(PipelineRun.id)).filter(PipelineRun.pipeline_name == name).scalar()
        ok = (db.query(func.count(PipelineRun.id))
              .filter(PipelineRun.pipeline_name == name, PipelineRun.status == "success").scalar())
        statuses.append({
            "pipeline": name, "display_name": display,
            "status": latest.status if latest else "never_run",
            "mode": latest.mode if latest else None,
            "last_run": latest.started_at.isoformat() if latest and latest.started_at else None,
            "completed_at": latest.completed_at.isoformat() if latest and latest.completed_at else None,
            "records_inserted": latest.records_inserted if latest else 0,
            "records_updated": latest.records_updated if latest else 0,
            "quality_issues": latest.quality_issues if latest else 0,
            "error_message": latest.error_message if latest and latest.status == "failed" else None,
            "total_runs": total,
            "success_rate": round(ok / total * 100, 1) if total else 0,
        })

    all_ok = all(s["status"] == "success" for s in statuses)
    any_failed = any(s["status"] == "failed" for s in statuses)
    return {
        "overall_health": "healthy" if all_ok else ("degraded" if any_failed else "initialising"),
        "pipelines": statuses,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
def get_pipeline_history(
    pipeline: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Deprecated alias for page_size"),
    db: Session = Depends(get_db),
):
    """Paginated audit log of every ETL run (newest first)."""
    page_size = limit or page_size
    q = db.query(PipelineRun)
    if pipeline:
        q = q.filter(PipelineRun.pipeline_name == pipeline)
    total = q.count()
    runs = (q.order_by(desc(PipelineRun.started_at), desc(PipelineRun.id))
            .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total, "page": page, "page_size": page_size, "pages": max(1, math.ceil(total / page_size)),
        "runs": [{
            "id": r.id, "pipeline": r.pipeline_name,
            "display_name": PIPELINE_NAMES.get(r.pipeline_name, r.pipeline_name),
            "status": r.status, "mode": r.mode,
            "records_fetched": r.records_fetched, "records_inserted": r.records_inserted,
            "records_updated": r.records_updated, "records_skipped": r.records_skipped,
            "quality_issues": r.quality_issues, "watermark": r.watermark,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error_message": r.error_message,
            "duration_seconds": ((r.completed_at - r.started_at).total_seconds()
                                 if r.completed_at and r.started_at else None),
        } for r in runs],
    }


@router.get("/quality")
def get_quality_issues(
    pipeline: Optional[str] = None,
    severity: Optional[str] = Query(None, enum=["error", "warning"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Paginated data-quality issues found by the validation layer."""
    q = db.query(DataQualityIssue)
    if pipeline:
        q = q.filter(DataQualityIssue.pipeline_name == pipeline)
    if severity:
        q = q.filter(DataQualityIssue.severity == severity)
    total = q.count()
    rows = (q.order_by(desc(DataQualityIssue.id)).offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total, "page": page, "page_size": page_size, "pages": max(1, math.ceil(total / page_size)),
        "issues": [{
            "id": i.id, "run_id": i.run_id, "pipeline": i.pipeline_name,
            "display_name": PIPELINE_NAMES.get(i.pipeline_name, i.pipeline_name),
            "severity": i.severity, "check": i.check, "key": i.key, "message": i.message, "value": i.value,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        } for i in rows],
    }


@router.get("/cache")
def get_cache_stats():
    """In-process API cache statistics."""
    return cache.stats()


@router.post("/refresh", dependencies=[Depends(require_api_key)])
def trigger_refresh(
    background_tasks: BackgroundTasks,
    pipeline: str = "all",
):
    """
    Manually trigger a pipeline run. Protected by `X-API-Key` when API_KEY is configured.
    pipeline: all | abs_labour_force | abs_cpi | abs_building_approvals | nsw_crime
    """
    if pipeline not in HANDLERS:
        raise HTTPException(400, f"Unknown pipeline '{pipeline}'. Choose from: {list(HANDLERS)}")
    background_tasks.add_task(HANDLERS[pipeline])
    return {"message": f"Pipeline '{pipeline}' triggered", "triggered_at": datetime.now(timezone.utc).isoformat()}
