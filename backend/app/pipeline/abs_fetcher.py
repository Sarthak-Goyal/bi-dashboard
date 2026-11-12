"""
ABS Data API pipelines (SDMX-JSON): Labour Force, CPI, Building Approvals.
Source: https://api.data.abs.gov.au/

All three run through the generic incremental engine in engine.py.
"""

import logging
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BuildingApprovalRecord, CPIRecord, LabourForceRecord, PipelineRun
from app.pipeline import common, sample_data
from app.pipeline.engine import EtlJob, run_etl
from app.pipeline.quality import Spec
from app.pipeline.sdmx import parse_sdmx_json

logger = logging.getLogger(__name__)


def _abs_fetch(path: str):
    def fetch(start: str) -> pd.DataFrame:
        url = f"{get_settings().abs_base_url}/{path}?startPeriod={start}&format=jsondata"
        return parse_sdmx_json(common.http_get_json(url, headers=common.ABS_HEADERS))
    return fetch


# ── Labour Force ─────────────────────────────────────────────────────────────
# Dataflow LF, key M6+M7.20.1+9.3.1599.M  (measure.tsest.region.sex.age.freq)
# M6 = unemployment rate, M7 = participation rate; region 1 = NSW, 9 = Australia

_MEASURES = {"Unemployment rate": "unemployment_rate", "Participation rate": "participation_rate"}
_REGIONS = {"New South Wales": "NSW", "Australia": "AUS"}


def _labour_prepare(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw
    df = raw.copy()
    df["metric"] = df.get("MEASURE", pd.Series(dtype=str)).map(_MEASURES)
    df["region"] = df.get("REGION", pd.Series(dtype=str)).map(_REGIONS)
    return df.dropna(subset=["metric", "region"])[["period", "region", "metric", "value"]]


def _labour_rows(db: Session, df: pd.DataFrame) -> list[dict]:
    return [dict(period=r.period, region=r.region, metric=r.metric, value=float(r.value),
                 adjustment="Seasonally Adjusted", unit="%") for r in df.itertuples()]


LABOUR_JOB = EtlJob(
    name="abs_labour_force", label="ABS Labour Force",
    source_url="https://api.data.abs.gov.au/data/LF/M6+M7.20.1+9.3.1599.M",
    model=LabourForceRecord, key_fields=("period", "region", "metric"), value_fields=("value",),
    watermark_col=LabourForceRecord.period, freq="M", default_start="2020-01", lookback=3,
    quality=Spec("labour_force", group_cols=("region", "metric"), freq="M", min_value=0, max_value=100,
                 required_cols=("region", "metric")),
    fetch=_abs_fetch("LF/M6+M7.20.1+9.3.1599.M"),
    prepare=_labour_prepare, to_rows=_labour_rows,
    window=lambda start: LabourForceRecord.period >= start,
    sample_rows=sample_data.sample_labour_force,
)


# ── CPI ──────────────────────────────────────────────────────────────────────
# Dataflow CPI, key 1.1.10.Q  (index 1 = All groups, region 10 = Sydney)

def _cpi_prepare(raw: pd.DataFrame) -> pd.DataFrame:
    return raw[["period", "value"]] if not raw.empty else raw


def _cpi_rows(db: Session, df: pd.DataFrame) -> list[dict]:
    """
    Annual % change needs the value four quarters earlier, which may lie outside
    an incremental fetch window — so merge in what is already stored first.
    """
    stored = {r.period: r.index_value for r in db.query(CPIRecord)
              .filter(CPIRecord.is_synthetic.is_(False)).all()}
    fetched = {r.period: float(r.value) for r in df.itertuples()}
    combined = {**stored, **fetched}
    ordered = sorted(combined)
    rows = []
    for i, period in enumerate(ordered):
        if period not in fetched:
            continue
        prior = combined[ordered[i - 4]] if i >= 4 else None
        pct = round((combined[period] / prior - 1) * 100, 2) if prior else None
        rows.append(dict(period=period, region="Sydney", series="All Groups CPI",
                         index_value=round(combined[period], 1), pct_change_annual=pct))
    return rows


CPI_JOB = EtlJob(
    name="abs_cpi", label="ABS CPI",
    source_url="https://api.data.abs.gov.au/data/CPI/1.1.10.Q",
    model=CPIRecord, key_fields=("period", "region", "series"), value_fields=("index_value", "pct_change_annual"),
    watermark_col=CPIRecord.period, freq="Q", default_start="2020-Q1", lookback=6,
    quality=Spec("cpi", freq="Q", min_value=20, max_value=1000),
    fetch=_abs_fetch("CPI/1.1.10.Q"),
    prepare=_cpi_prepare, to_rows=_cpi_rows,
    window=lambda start: CPIRecord.period >= start,
    sample_rows=sample_data.sample_cpi,
)


# ── Building Approvals ───────────────────────────────────────────────────────
# Dataflow BA_GCCSA (monthly). The exact series key is not hard-coded: the whole
# flow is requested and filtered by dimension *labels*, so a reordered key does not
# break it. NOTE: this endpoint is unverified against the live API — if the labels
# change the quality layer/audit log report it and the pipeline falls back to sample data.

def _ba_prepare(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw
    dims = [c for c in raw.columns if c not in ("period", "value")]
    text = raw[dims].astype(str).apply(lambda col: col.str.lower())
    joined = text.agg(" | ".join, axis=1)
    mask = (
        joined.str.contains("new south wales")
        & joined.str.contains("dwelling")
        & joined.str.contains("total")
        & ~joined.str.contains("value")
    )
    df = raw[mask].copy()
    if df.empty:
        return df
    # Several adjustment types may remain (original / seasonally adjusted / trend); prefer "original"
    j = joined[mask]
    df["_rank"] = j.str.contains("original").map({True: 0, False: 1})
    df = df.sort_values(["period", "_rank"]).drop_duplicates("period", keep="first")
    return df[["period", "value"]]


def _ba_rows(db: Session, df: pd.DataFrame) -> list[dict]:
    return [dict(period=r.period, region="NSW", building_type="Total dwelling units",
                 value=float(r.value), unit="dwellings") for r in df.itertuples()]


BUILDING_JOB = EtlJob(
    name="abs_building_approvals", label="ABS Building Approvals",
    source_url="https://api.data.abs.gov.au/data/BA_GCCSA",
    model=BuildingApprovalRecord, key_fields=("period", "region", "building_type"), value_fields=("value",),
    watermark_col=BuildingApprovalRecord.period, freq="M", default_start="2020-01", lookback=3,
    quality=Spec("building_approvals", freq="M", min_value=0, max_value=100_000),
    fetch=_abs_fetch("BA_GCCSA/all"),
    prepare=_ba_prepare, to_rows=_ba_rows,
    window=lambda start: BuildingApprovalRecord.period >= start,
    sample_rows=sample_data.sample_building_approvals,
)


def fetch_labour_force(db: Session) -> PipelineRun:
    return run_etl(db, LABOUR_JOB)


def fetch_cpi(db: Session) -> PipelineRun:
    return run_etl(db, CPI_JOB)


def fetch_building_approvals(db: Session) -> PipelineRun:
    return run_etl(db, BUILDING_JOB)
