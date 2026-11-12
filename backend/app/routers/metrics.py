"""
/api/metrics/* — data endpoints consumed by the frontend dashboard.

Read-heavy endpoints go through a small TTL cache (app/cache.py) that is cleared
whenever a pipeline run finishes.
"""

import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app import cache
from app.database import get_db
from app.models import (
    BuildingApprovalRecord, CPIRecord, LabourForceRecord, NSWCrimeRecord,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

DATASETS = {
    "labour_force": LabourForceRecord,
    "cpi": CPIRecord,
    "building_approvals": BuildingApprovalRecord,
    "crime": NSWCrimeRecord,
}


def _cached(response: Response, key: str, producer):
    value, hit = cache.get_or_set(key, producer)
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


def _clean(v):
    """JSON cannot carry NaN."""
    return None if isinstance(v, float) and math.isnan(v) else v


# ── Data provenance ──────────────────────────────────────────────────────────

def data_mode(db: Session) -> dict:
    """Which datasets are live, sample, or empty — so the UI never passes sample data off as real."""
    per: dict[str, str] = {}
    for name, model in DATASETS.items():
        synth = db.query(model.id).filter(model.is_synthetic.is_(True)).first() is not None
        real = db.query(model.id).filter(model.is_synthetic.is_(False)).first() is not None
        per[name] = "mixed" if synth and real else "sample" if synth else "live" if real else "empty"
    states = set(per.values()) - {"empty"}
    overall = "empty" if not states else states.pop() if len(states) == 1 else "mixed"
    return {"overall": overall, "datasets": per,
            "sample_datasets": [k for k, v in per.items() if v in ("sample", "mixed")]}


@router.get("/data-mode")
def get_data_mode(response: Response, db: Session = Depends(get_db)):
    return _cached(response, "data-mode", lambda: data_mode(db))


# ── KPI Summary ──────────────────────────────────────────────────────────────

def _latest_two(db: Session, model, *filters):
    rows = (db.query(model).filter(*filters).order_by(desc(model.period)).limit(2).all())
    return (rows[0] if rows else None, rows[1] if len(rows) > 1 else None)


def _build_summary(db: Session) -> dict:
    unemp, unemp_prev = _latest_two(db, LabourForceRecord, LabourForceRecord.region == "NSW",
                                    LabourForceRecord.metric == "unemployment_rate")
    part, part_prev = _latest_two(db, LabourForceRecord, LabourForceRecord.region == "NSW",
                                  LabourForceRecord.metric == "participation_rate")
    cpi = (db.query(CPIRecord).filter(CPIRecord.region == "Sydney")
           .order_by(desc(CPIRecord.period)).first())
    approvals, approvals_prev = _latest_two(db, BuildingApprovalRecord, BuildingApprovalRecord.region == "NSW")

    latest_year = db.query(func.max(NSWCrimeRecord.year)).scalar()

    def crime_total(year):
        if year is None:
            return 0
        return db.query(func.sum(NSWCrimeRecord.incidents_recorded)).filter(NSWCrimeRecord.year == year).scalar() or 0

    crime, prev_crime = crime_total(latest_year), crime_total(latest_year - 1 if latest_year else None)

    def delta(a, b):
        return round(a.value - b.value, 2) if a and b else None

    return {
        "data_mode": data_mode(db),
        "unemployment_rate": {
            "value": round(unemp.value, 2) if unemp else None, "period": unemp.period if unemp else None,
            "delta": delta(unemp, unemp_prev), "unit": "%", "region": "NSW",
            "label": "Unemployment Rate", "description": "Seasonally adjusted, persons",
        },
        "participation_rate": {
            "value": round(part.value, 2) if part else None, "period": part.period if part else None,
            "delta": delta(part, part_prev), "unit": "%", "region": "NSW",
            "label": "Participation Rate", "description": "Seasonally adjusted, persons",
        },
        "cpi_annual_change": {
            "value": cpi.pct_change_annual if cpi else None, "period": cpi.period if cpi else None,
            "index_value": cpi.index_value if cpi else None, "unit": "%", "region": "Sydney",
            "label": "CPI Annual Change", "description": "All groups, Sydney",
        },
        "building_approvals": {
            "value": int(approvals.value) if approvals else None, "period": approvals.period if approvals else None,
            "delta_pct": round((approvals.value / approvals_prev.value - 1) * 100, 1)
                if approvals and approvals_prev and approvals_prev.value else None,
            "unit": "dwellings", "region": "NSW",
            "label": "Dwelling Approvals", "description": "NSW, total dwelling units / month",
        },
        "crime_incidents": {
            "value": int(crime) if crime else 0, "year": latest_year,
            "delta_pct": round((crime - prev_crime) / prev_crime * 100, 1) if crime and prev_crime else None,
            "unit": "incidents", "region": "NSW", "label": "Recorded Crime",
            "description": f"All offences, {latest_year}" if latest_year else "No data yet",
        },
    }


@router.get("/summary")
def get_summary(response: Response, db: Session = Depends(get_db)):
    """Headline KPI cards for the dashboard hero row."""
    return _cached(response, "summary", lambda: _build_summary(db))


# ── Labour Force ─────────────────────────────────────────────────────────────

@router.get("/unemployment")
def get_unemployment(
    response: Response,
    region: str = Query("NSW", enum=["NSW", "AUS"]),
    months: int = Query(36, ge=0, le=240, description="0 = all available"),
    db: Session = Depends(get_db),
):
    """Monthly unemployment + participation rate for one region."""
    def build():
        rows = db.query(LabourForceRecord).filter(LabourForceRecord.region == region).all()
        pivot: dict[str, dict] = {}
        for r in rows:
            pivot.setdefault(r.period, {})[r.metric] = round(r.value, 2)
        series = [{"period": p, **v} for p, v in sorted(pivot.items())]
        return {"region": region, "series": series[-months:] if months else series}
    return _cached(response, f"unemp:{region}:{months}", build)


@router.get("/unemployment/compare")
def compare_unemployment(
    response: Response,
    months: int = Query(24, ge=0, le=240, description="0 = all available"),
    db: Session = Depends(get_db),
):
    """NSW vs Australia unemployment rate."""
    def build():
        rows = (db.query(LabourForceRecord).filter(LabourForceRecord.metric == "unemployment_rate")
                .order_by(LabourForceRecord.period).all())
        by_period: dict[str, dict] = {}
        for r in rows:
            by_period.setdefault(r.period, {})[r.region] = round(r.value, 2)
        series = [{"period": p, "NSW": d.get("NSW"), "AUS": d.get("AUS")} for p, d in sorted(by_period.items())]
        return {"series": series[-months:] if months else series}
    return _cached(response, f"unemp-compare:{months}", build)


# ── CPI ──────────────────────────────────────────────────────────────────────

@router.get("/cpi")
def get_cpi(
    response: Response,
    quarters: int = Query(20, ge=0, le=80, description="0 = all available"),
    db: Session = Depends(get_db),
):
    """Sydney CPI index value + annual % change."""
    def build():
        rows = db.query(CPIRecord).filter(CPIRecord.region == "Sydney").order_by(CPIRecord.period).all()
        series = [{"period": r.period, "index_value": r.index_value, "pct_change_annual": r.pct_change_annual}
                  for r in rows]
        return {"region": "Sydney", "series": series[-quarters:] if quarters else series}
    return _cached(response, f"cpi:{quarters}", build)


# ── Housing × Labour × CPI  (multi-source join) ──────────────────────────────

def _month_to_quarter(period: str) -> str:
    y, m = period.split("-")
    return f"{y}-Q{(int(m) - 1) // 3 + 1}"


@router.get("/housing-labour")
def housing_labour(
    response: Response,
    months: int = Query(36, ge=0, le=240, description="0 = all available"),
    db: Session = Depends(get_db),
):
    """
    Three ABS sources joined on time:
      building approvals (monthly)  ⨝  unemployment rate (monthly)  ⟕  CPI annual change (quarterly → its months).
    Includes the Pearson correlation of approvals vs unemployment over the overlap.
    """
    def build():
        ba = pd.DataFrame([(r.period, r.value) for r in db.query(BuildingApprovalRecord)
                           .filter(BuildingApprovalRecord.region == "NSW")], columns=["period", "approvals"])
        ue = pd.DataFrame([(r.period, r.value) for r in db.query(LabourForceRecord)
                           .filter(LabourForceRecord.region == "NSW",
                                   LabourForceRecord.metric == "unemployment_rate")],
                          columns=["period", "unemployment_rate"])
        cpi = pd.DataFrame([(r.period, r.pct_change_annual) for r in db.query(CPIRecord)
                            .filter(CPIRecord.region == "Sydney")], columns=["quarter", "cpi_annual"])
        if ba.empty or ue.empty:
            return {"series": [], "stats": {"n": 0, "correlation": None}, "sources": ["building_approvals", "labour_force", "cpi"]}

        df = ba.merge(ue, on="period", how="inner").sort_values("period")
        df["quarter"] = df["period"].map(_month_to_quarter)
        df = df.merge(cpi, on="quarter", how="left").drop(columns="quarter")
        df["approvals_3m_avg"] = df["approvals"].rolling(3, min_periods=1).mean().round(0)

        corr = df["approvals"].corr(df["unemployment_rate"]) if len(df) >= 6 else None
        out = df.tail(months) if months else df
        return {
            "series": [{k: _clean(v) for k, v in rec.items()} for rec in out.to_dict("records")],
            "stats": {"n": int(len(df)), "correlation": None if corr is None or math.isnan(corr) else round(float(corr), 3),
                      "note": "Computed across all overlapping months; correlation does not imply causation."},
            "sources": ["building_approvals", "labour_force", "cpi"],
        }
    return _cached(response, f"housing:{months}", build)


# ── NSW Crime ────────────────────────────────────────────────────────────────

def _latest_year(db: Session, year: Optional[int]) -> Optional[int]:
    return year if year is not None else db.query(func.max(NSWCrimeRecord.year)).scalar()


@router.get("/crime/by-offence")
def crime_by_offence(response: Response, year: Optional[int] = None, db: Session = Depends(get_db)):
    def build():
        y = _latest_year(db, year)
        rows = (db.query(NSWCrimeRecord.offence_category, func.sum(NSWCrimeRecord.incidents_recorded).label("total"))
                .filter(NSWCrimeRecord.year == y).group_by(NSWCrimeRecord.offence_category)
                .order_by(desc("total")).all())
        return {"year": y, "series": [{"offence": r.offence_category, "total": int(r.total)} for r in rows]}
    return _cached(response, f"crime-offence:{year}", build)


@router.get("/crime/offences")
def crime_offences(response: Response, db: Session = Depends(get_db)):
    """Offence categories present in the data (drives the UI selectors)."""
    def build():
        rows = (db.query(NSWCrimeRecord.offence_category, func.sum(NSWCrimeRecord.incidents_recorded).label("t"))
                .group_by(NSWCrimeRecord.offence_category).order_by(desc("t")).all())
        return {"offences": [r.offence_category for r in rows]}
    return _cached(response, "crime-offences", build)


@router.get("/crime/trend")
def crime_trend(
    response: Response,
    offence: str = Query("Theft"),
    top_lgas: int = Query(5, ge=1, le=10),
    years: int = Query(0, ge=0, le=30, description="Most recent N years; 0 = all"),
    db: Session = Depends(get_db),
):
    """Year-on-year trend for one offence category across the top N LGAs."""
    def build():
        top = (db.query(NSWCrimeRecord.lga_name, func.sum(NSWCrimeRecord.incidents_recorded).label("total"))
               .filter(NSWCrimeRecord.offence_category == offence).group_by(NSWCrimeRecord.lga_name)
               .order_by(desc("total")).limit(top_lgas).all())
        lgas = [r.lga_name for r in top]
        rows = (db.query(NSWCrimeRecord).filter(NSWCrimeRecord.offence_category == offence,
                                                NSWCrimeRecord.lga_name.in_(lgas))
                .order_by(NSWCrimeRecord.year).all())
        by_year: dict[int, dict] = {}
        for r in rows:
            by_year.setdefault(r.year, {})[r.lga_name] = r.incidents_recorded
        series = [{"year": y, **v} for y, v in sorted(by_year.items())]
        return {"offence": offence, "lgas": lgas, "series": series[-years:] if years else series}
    return _cached(response, f"crime-trend:{offence}:{top_lgas}:{years}", build)


@router.get("/crime/top-lgas")
def crime_top_lgas(response: Response, year: Optional[int] = None,
                   limit: int = Query(10, ge=3, le=30), db: Session = Depends(get_db)):
    def build():
        y = _latest_year(db, year)
        rows = (db.query(NSWCrimeRecord.lga_name, func.sum(NSWCrimeRecord.incidents_recorded).label("total"))
                .filter(NSWCrimeRecord.year == y).group_by(NSWCrimeRecord.lga_name)
                .order_by(desc("total")).limit(limit).all())
        return {"year": y, "series": [{"lga": r.lga_name, "total": int(r.total)} for r in rows]}
    return _cached(response, f"crime-top:{year}:{limit}", build)


@router.get("/crime/by-lga")
def crime_by_lga(
    response: Response,
    year: Optional[int] = None,
    offence: str = Query("All"),
    db: Session = Depends(get_db),
):
    """Incidents and rate per 100k for every LGA — feeds the choropleth map."""
    def build():
        y = _latest_year(db, year)
        q = db.query(NSWCrimeRecord).filter(NSWCrimeRecord.year == y)
        rows = q.all()
        if not rows:
            return {"year": y, "offence": offence, "series": []}
        df = pd.DataFrame([(r.lga_name, r.offence_category, r.incidents_recorded, r.rate_per_100k) for r in rows],
                          columns=["lga", "offence", "incidents", "rate"])
        # Population estimate per LGA from incidents/rate (median across offences)
        valid = df[(df["rate"] > 0) & (df["incidents"] > 0)].copy()
        valid["pop"] = valid["incidents"] / valid["rate"] * 100_000
        pop = valid.groupby("lga")["pop"].median()
        sel = df if offence == "All" else df[df["offence"] == offence]
        agg = sel.groupby("lga")["incidents"].sum()
        out = []
        for lga, inc in agg.items():
            p = pop.get(lga)
            out.append({"lga": lga, "incidents": int(inc),
                        "rate_per_100k": round(float(inc) / p * 100_000, 1) if p and not math.isnan(p) else None})
        out.sort(key=lambda r: r["incidents"], reverse=True)
        return {"year": y, "offence": offence, "series": out}
    return _cached(response, f"crime-lga:{year}:{offence}", build)


# ── Paginated raw records ────────────────────────────────────────────────────

@router.get("/records/{dataset}")
def get_records(
    dataset: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Paginated raw rows for any dataset (newest first). Response envelope carries totals."""
    model = DATASETS.get(dataset)
    if model is None:
        raise HTTPException(404, f"Unknown dataset '{dataset}'. Choose from: {sorted(DATASETS)}")
    order = desc(model.year) if dataset == "crime" else desc(model.period)
    total = db.query(func.count(model.id)).scalar() or 0
    rows = db.query(model).order_by(order, model.id).offset((page - 1) * page_size).limit(page_size).all()
    cols = [c.name for c in model.__table__.columns if c.name not in ("created_at",)]
    items = []
    for r in rows:
        item = {c: getattr(r, c) for c in cols}
        if item.get("updated_at"):
            item["updated_at"] = item["updated_at"].isoformat()
        items.append(item)
    return {"dataset": dataset, "total": total, "page": page, "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)), "items": items}
