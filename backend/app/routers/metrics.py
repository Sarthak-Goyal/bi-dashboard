"""
/api/metrics/* — all data endpoints consumed by the frontend dashboard.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models import LabourForceRecord, CPIRecord, NSWCrimeRecord

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# ── KPI Summary ───────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """
    Four headline KPI cards for the dashboard hero row:
      - NSW unemployment rate (latest)
      - NSW participation rate (latest)
      - Sydney CPI annual change (latest)
      - Total NSW crime incidents (latest full year)
    """
    # Latest unemployment rate NSW
    unemp = (
        db.query(LabourForceRecord)
        .filter(LabourForceRecord.region == "NSW",
                LabourForceRecord.metric == "unemployment_rate")
        .order_by(desc(LabourForceRecord.period))
        .first()
    )
    # Previous period for delta
    unemp_prev = None
    if unemp:
        unemp_prev = (
            db.query(LabourForceRecord)
            .filter(LabourForceRecord.region == "NSW",
                    LabourForceRecord.metric == "unemployment_rate",
                    LabourForceRecord.period < unemp.period)
            .order_by(desc(LabourForceRecord.period))
            .first()
        )

    # Latest participation rate NSW
    part = (
        db.query(LabourForceRecord)
        .filter(LabourForceRecord.region == "NSW",
                LabourForceRecord.metric == "participation_rate")
        .order_by(desc(LabourForceRecord.period))
        .first()
    )
    part_prev = None
    if part:
        part_prev = (
            db.query(LabourForceRecord)
            .filter(LabourForceRecord.region == "NSW",
                    LabourForceRecord.metric == "participation_rate",
                    LabourForceRecord.period < part.period)
            .order_by(desc(LabourForceRecord.period))
            .first()
        )

    # Latest CPI annual change
    cpi = (
        db.query(CPIRecord)
        .filter(CPIRecord.region == "Sydney")
        .order_by(desc(CPIRecord.period))
        .first()
    )

    # Total crime — latest full year
    latest_crime_year = db.query(func.max(NSWCrimeRecord.year)).scalar()
    crime_total = (
        db.query(func.sum(NSWCrimeRecord.incidents_recorded))
        .filter(NSWCrimeRecord.year == latest_crime_year)
        .scalar()
    ) if latest_crime_year else 0

    prev_crime_total = (
        db.query(func.sum(NSWCrimeRecord.incidents_recorded))
        .filter(NSWCrimeRecord.year == (latest_crime_year - 1))
        .scalar()
    ) if latest_crime_year else 0

    return {
        "unemployment_rate": {
            "value": round(unemp.value, 2) if unemp else None,
            "period": unemp.period if unemp else None,
            "delta": round(unemp.value - unemp_prev.value, 2) if unemp and unemp_prev else None,
            "unit": "%",
            "region": "NSW",
            "label": "Unemployment Rate",
            "description": "Seasonally adjusted, persons",
        },
        "participation_rate": {
            "value": round(part.value, 2) if part else None,
            "period": part.period if part else None,
            "delta": round(part.value - part_prev.value, 2) if part and part_prev else None,
            "unit": "%",
            "region": "NSW",
            "label": "Participation Rate",
            "description": "Seasonally adjusted, persons",
        },
        "cpi_annual_change": {
            "value": cpi.pct_change_annual if cpi else None,
            "period": cpi.period if cpi else None,
            "index_value": cpi.index_value if cpi else None,
            "unit": "%",
            "region": "Sydney",
            "label": "CPI Annual Change",
            "description": "All groups, Sydney",
        },
        "crime_incidents": {
            "value": int(crime_total) if crime_total else 0,
            "year": latest_crime_year,
            "delta_pct": round(((crime_total - prev_crime_total) / prev_crime_total) * 100, 1)
                if crime_total and prev_crime_total else None,
            "unit": "incidents",
            "region": "NSW",
            "label": "Recorded Crime",
            "description": f"All offences, {latest_crime_year}",
        },
    }


# ── Labour Force Time Series ──────────────────────────────────────────────────

@router.get("/unemployment")
def get_unemployment(
    region: str = Query("NSW", enum=["NSW", "AUS"]),
    months: int = Query(36, ge=6, le=120),
    db: Session = Depends(get_db),
):
    """Monthly unemployment + participation rate for chart (last N months)."""
    records = (
        db.query(LabourForceRecord)
        .filter(LabourForceRecord.region == region)
        .order_by(desc(LabourForceRecord.period))
        .limit(months * 2)          # ×2 because we have 2 metrics per period
        .all()
    )

    # Pivot into {period: {metric: value}}
    pivot: dict[str, dict] = {}
    for r in records:
        pivot.setdefault(r.period, {})[r.metric] = round(r.value, 2)

    series = sorted([
        {"period": p, **vals}
        for p, vals in pivot.items()
    ], key=lambda x: x["period"])

    # Last 36 months
    return {"region": region, "series": series[-months:]}


@router.get("/unemployment/compare")
def compare_unemployment(db: Session = Depends(get_db)):
    """NSW vs AUS unemployment rate side-by-side for last 24 months."""
    records = (
        db.query(LabourForceRecord)
        .filter(LabourForceRecord.metric == "unemployment_rate")
        .order_by(LabourForceRecord.period)
        .all()
    )
    # Group by period
    by_period: dict[str, dict] = {}
    for r in records:
        by_period.setdefault(r.period, {})[r.region] = round(r.value, 2)

    series = [
        {"period": p, "NSW": d.get("NSW"), "AUS": d.get("AUS")}
        for p, d in sorted(by_period.items())
    ]
    return {"series": series[-24:]}


# ── CPI ───────────────────────────────────────────────────────────────────────

@router.get("/cpi")
def get_cpi(quarters: int = Query(20, ge=4, le=40), db: Session = Depends(get_db)):
    """Sydney CPI index value + annual % change, last N quarters."""
    records = (
        db.query(CPIRecord)
        .filter(CPIRecord.region == "Sydney")
        .order_by(CPIRecord.period)
        .all()
    )
    series = [
        {
            "period": r.period,
            "index_value": r.index_value,
            "pct_change_annual": r.pct_change_annual,
        }
        for r in records
    ]
    return {"region": "Sydney", "series": series[-quarters:]}


# ── NSW Crime ─────────────────────────────────────────────────────────────────

@router.get("/crime/by-offence")
def crime_by_offence(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Total incidents by offence category across all LGAs for a given year."""
    if year is None:
        year = db.query(func.max(NSWCrimeRecord.year)).scalar()

    rows = (
        db.query(
            NSWCrimeRecord.offence_category,
            func.sum(NSWCrimeRecord.incidents_recorded).label("total"),
        )
        .filter(NSWCrimeRecord.year == year)
        .group_by(NSWCrimeRecord.offence_category)
        .order_by(desc("total"))
        .all()
    )
    return {
        "year": year,
        "series": [{"offence": r.offence_category, "total": int(r.total)} for r in rows],
    }


@router.get("/crime/trend")
def crime_trend(
    offence: str = Query("Theft"),
    top_lgas: int = Query(5),
    db: Session = Depends(get_db),
):
    """Year-on-year trend for a single offence category, top N LGAs."""
    # Get top LGAs by total incidents for this offence
    top = (
        db.query(NSWCrimeRecord.lga_name,
                 func.sum(NSWCrimeRecord.incidents_recorded).label("total"))
        .filter(NSWCrimeRecord.offence_category == offence)
        .group_by(NSWCrimeRecord.lga_name)
        .order_by(desc("total"))
        .limit(top_lgas)
        .all()
    )
    lga_names = [r.lga_name for r in top]

    records = (
        db.query(NSWCrimeRecord)
        .filter(NSWCrimeRecord.offence_category == offence,
                NSWCrimeRecord.lga_name.in_(lga_names))
        .order_by(NSWCrimeRecord.year)
        .all()
    )

    # Build {year: {lga: value}}
    by_year: dict[int, dict] = {}
    for r in records:
        by_year.setdefault(r.year, {})[r.lga_name] = r.incidents_recorded

    series = [{"year": yr, **vals} for yr, vals in sorted(by_year.items())]
    return {"offence": offence, "lgas": lga_names, "series": series}


@router.get("/crime/top-lgas")
def crime_top_lgas(
    year: Optional[int] = None,
    limit: int = Query(10, ge=3, le=20),
    db: Session = Depends(get_db),
):
    """Top LGAs by total recorded incidents for a given year."""
    if year is None:
        year = db.query(func.max(NSWCrimeRecord.year)).scalar()

    rows = (
        db.query(
            NSWCrimeRecord.lga_name,
            func.sum(NSWCrimeRecord.incidents_recorded).label("total"),
        )
        .filter(NSWCrimeRecord.year == year)
        .group_by(NSWCrimeRecord.lga_name)
        .order_by(desc("total"))
        .limit(limit)
        .all()
    )
    return {
        "year": year,
        "series": [{"lga": r.lga_name, "total": int(r.total)} for r in rows],
    }
