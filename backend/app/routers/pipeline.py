"""
/api/pipeline/* — pipeline status, history, and manual trigger endpoints.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models import PipelineRun
from app.pipeline.scheduler import run_all_pipelines, run_labour_force_only, run_cpi_only, run_crime_only

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

PIPELINE_NAMES = {
    "abs_labour_force": "ABS Labour Force",
    "abs_cpi": "ABS Consumer Price Index",
    "nsw_crime": "NSW Crime Statistics",
}


@router.get("/status")
def get_pipeline_status(db: Session = Depends(get_db)):
    """Latest run status for each pipeline + aggregate health."""
    statuses = []
    for internal_name, display_name in PIPELINE_NAMES.items():
        latest = (
            db.query(PipelineRun)
            .filter(PipelineRun.pipeline_name == internal_name)
            .order_by(desc(PipelineRun.started_at))
            .first()
        )
        total_runs = (
            db.query(func.count(PipelineRun.id))
            .filter(PipelineRun.pipeline_name == internal_name)
            .scalar()
        )
        success_runs = (
            db.query(func.count(PipelineRun.id))
            .filter(PipelineRun.pipeline_name == internal_name,
                    PipelineRun.status == "success")
            .scalar()
        )
        statuses.append({
            "pipeline": internal_name,
            "display_name": display_name,
            "status": latest.status if latest else "never_run",
            "last_run": latest.started_at.isoformat() if latest else None,
            "completed_at": latest.completed_at.isoformat() if latest and latest.completed_at else None,
            "records_inserted": latest.records_inserted if latest else 0,
            "error_message": latest.error_message if latest and latest.status == "failed" else None,
            "total_runs": total_runs,
            "success_rate": round((success_runs / total_runs) * 100, 1) if total_runs else 0,
        })

    overall = all(s["status"] == "success" for s in statuses)
    any_failed = any(s["status"] == "failed" for s in statuses)

    return {
        "overall_health": "healthy" if overall else ("degraded" if any_failed else "initialising"),
        "pipelines": statuses,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
def get_pipeline_history(
    pipeline: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Recent run history — optionally filtered by pipeline name."""
    q = db.query(PipelineRun).order_by(desc(PipelineRun.started_at))
    if pipeline:
        q = q.filter(PipelineRun.pipeline_name == pipeline)
    runs = q.limit(limit).all()
    return {
        "runs": [
            {
                "id": r.id,
                "pipeline": r.pipeline_name,
                "display_name": PIPELINE_NAMES.get(r.pipeline_name, r.pipeline_name),
                "status": r.status,
                "records_fetched": r.records_fetched,
                "records_inserted": r.records_inserted,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
                "duration_seconds": (
                    (r.completed_at - r.started_at).total_seconds()
                    if r.completed_at and r.started_at else None
                ),
            }
            for r in runs
        ]
    }


@router.post("/refresh")
def trigger_refresh(
    pipeline: str = "all",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger a pipeline run.
    pipeline: "all" | "abs_labour_force" | "abs_cpi" | "nsw_crime"
    """
    handlers = {
        "all": run_all_pipelines,
        "abs_labour_force": run_labour_force_only,
        "abs_cpi": run_cpi_only,
        "nsw_crime": run_crime_only,
    }
    if pipeline not in handlers:
        raise HTTPException(400, f"Unknown pipeline '{pipeline}'. Choose from: {list(handlers)}")

    background_tasks.add_task(handlers[pipeline])
    return {
        "message": f"Pipeline '{pipeline}' triggered",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }
