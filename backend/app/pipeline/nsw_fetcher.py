"""
NSW Open Data (CKAN) pipeline — BOCSAR recorded crime by LGA.
Source: https://data.nsw.gov.au  (no API key required)

NOTE: the CKAN resource id is configurable (CRIME_RESOURCE_ID) because dataset ids
change when BOCSAR republishes. If it cannot be read, the audit log records why and
clearly-labelled sample data is used instead.
"""

import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NSWCrimeRecord, PipelineRun
from app.pipeline import common, sample_data
from app.pipeline.engine import EtlJob, run_etl
from app.pipeline.quality import Spec

logger = logging.getLogger(__name__)

PAGE = 1000
MAX_PAGES = 60


def _fetch_ckan(start: str) -> pd.DataFrame:
    s = get_settings()
    url = f"{s.ckan_base_url}/datastore_search"
    records: list[dict] = []
    for page in range(MAX_PAGES):
        data = common.http_get_json(url, params={"resource_id": s.crime_resource_id,
                                                 "limit": PAGE, "offset": page * PAGE})
        if not data.get("success"):
            raise ValueError("CKAN reported success=false")
        batch = data["result"].get("records", [])
        records.extend(batch)
        if len(batch) < PAGE:
            break
    if not records:
        raise ValueError("CKAN returned no records")
    return pd.DataFrame(records)


_CANDIDATES = {
    "year": ["year", "calendar_year", "yr"],
    "lga": ["lga_name", "lga", "local_government_area", "area"],
    "offence": ["offence_category", "offence", "offence_type", "subcategory"],
    "incidents": ["incidents_recorded", "incidents", "count", "number"],
    "rate": ["rate_per_100_000", "rate_per_100k", "rate"],
}


def _detect_columns(df: pd.DataFrame) -> dict:
    lower = {c.lower().strip(): c for c in df.columns}
    found = {k: lower[a] for k, alts in _CANDIDATES.items() for a in alts if a in lower}
    required = {"year", "lga", "offence", "incidents"}
    return found if required <= found.keys() else {}


def _crime_prepare(raw: pd.DataFrame) -> pd.DataFrame:
    cols = _detect_columns(raw)
    if not cols:
        raise ValueError(f"Cannot map crime columns: {list(raw.columns)[:12]}")
    df = pd.DataFrame({
        "period": pd.to_numeric(raw[cols["year"]], errors="coerce"),
        "lga_name": raw[cols["lga"]].astype(str).str.replace(r"\s*\(NSW\)$", "", regex=True).str.strip(),
        "offence_category": raw[cols["offence"]].astype(str).str.strip(),
        "value": pd.to_numeric(raw[cols["incidents"]].astype(str).str.replace(",", ""), errors="coerce"),
        "rate": pd.to_numeric(raw[cols["rate"]], errors="coerce") if "rate" in cols else float("nan"),
    }).dropna(subset=["period"])
    df["period"] = df["period"].astype(int).astype(str)
    return df


def _crime_rows(db: Session, df: pd.DataFrame) -> list[dict]:
    return [dict(year=int(r.period), lga_name=r.lga_name, offence_category=r.offence_category,
                 incidents_recorded=int(r.value),
                 rate_per_100k=None if pd.isna(r.rate) else float(r.rate)) for r in df.itertuples()]


def _crime_job() -> EtlJob:
    return EtlJob(
        name="nsw_crime", label="NSW Crime",
        source_url=f"{get_settings().ckan_base_url}/datastore_search",
        model=NSWCrimeRecord, key_fields=("year", "lga_name", "offence_category"),
        value_fields=("incidents_recorded", "rate_per_100k"),
        watermark_col=NSWCrimeRecord.year, freq="A", default_start="2015", lookback=1,
        quality=Spec("nsw_crime", group_cols=("lga_name", "offence_category"), freq="A",
                     min_value=0, max_value=500_000, min_points_for_outliers=6,
                     required_cols=("lga_name", "offence_category")),
        fetch=_fetch_ckan, prepare=_crime_prepare, to_rows=_crime_rows,
        window=lambda start: NSWCrimeRecord.year >= int(start),
        sample_rows=sample_data.sample_crime,
    )


def fetch_nsw_crime(db: Session) -> PipelineRun:
    return run_etl(db, _crime_job())
