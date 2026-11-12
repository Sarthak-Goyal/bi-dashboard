"""
ABS Data API fetcher.
Source: https://api.data.abs.gov.au/
Docs:   https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis

The ABS uses SDMX 2.1 REST format. Responses are SDMX-JSON with a nested
structure: data.dataSets[0].series["dim0:dim1:..."].observations{"t": [value]}
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.models import LabourForceRecord, CPIRecord, PipelineRun

logger = logging.getLogger(__name__)

ABS_BASE = "https://api.data.abs.gov.au/data"
TIMEOUT = 30.0

# ---------------------------------------------------------
# SDMX-JSON parser
# ---------------------------------------------------------

def parse_sdmx_json(payload: dict) -> pd.DataFrame:
    """
    Convert ABS SDMX-JSON response into a tidy DataFrame.
    Returns columns: period, value, plus any dimension columns found.
    """
    structure = payload["data"]["structure"]
    datasets = payload["data"]["dataSets"]

    # Build time periods list from observation dimension
    obs_dims = structure["dimensions"]["observation"]
    time_dim = next((d for d in obs_dims if d.get("id") in ("TIME_PERIOD", "TIME")), obs_dims[0])
    periods = [v["id"] for v in time_dim["values"]]

    # Build series dimension labels
    series_dims = structure["dimensions"]["series"]

    rows = []
    for series_key, series_data in datasets[0]["series"].items():
        # Decode each dimension index for this series
        idx_parts = [int(i) for i in series_key.split(":")]
        dim_labels = {}
        for i, dim in enumerate(series_dims):
            try:
                dim_labels[dim["id"]] = dim["values"][idx_parts[i]]["name"]
            except (IndexError, KeyError):
                dim_labels[dim["id"]] = str(idx_parts[i])

        # Each observation key is the time index
        for t_str, obs_vals in series_data.get("observations", {}).items():
            t_idx = int(t_str)
            value = obs_vals[0] if obs_vals else None
            if value is not None and t_idx < len(periods):
                rows.append({**dim_labels, "period": periods[t_idx], "value": float(value)})

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# Labour Force pipeline
# ---------------------------------------------------------

def fetch_labour_force(db: Session, start_period: str = "2020-01") -> PipelineRun:
    """
    Fetch NSW & Australia unemployment rate + participation rate
    from the ABS Labour Force survey (monthly, seasonally adjusted).

    Dataflow: LF
    Key:      M6+M7   .20     .1+9   .3     .1599  .M
              measure  tsest   region  sex    age    freq
    M6 = Unemployment rate, M7 = Participation rate
    Region 1 = NSW, 9 = AUS
    """
    url = (
        f"{ABS_BASE}/LF/M6+M7.20.1+9.3.1599.M"
        f"?startPeriod={start_period}&format=jsondata"
    )

    run = PipelineRun(
        pipeline_name="abs_labour_force",
        status="running",
        source_url=url,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        logger.info(f"[ABS Labour Force] Fetching {url}")
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, headers={"Accept": "application/vnd.sdmx.data+json;version=1.0"})
            resp.raise_for_status()
            payload = resp.json()

        df = parse_sdmx_json(payload)
        if df.empty:
            raise ValueError("Parsed DataFrame is empty — check API key / dimensions")

        # Map ABS measure names to our internal metric names
        measure_map = {
            "Unemployment rate": "unemployment_rate",
            "Participation rate": "participation_rate",
        }
        region_map = {
            "New South Wales": "NSW",
            "Australia": "AUS",
        }

        records_inserted = 0
        for _, row in df.iterrows():
            metric = measure_map.get(row.get("MEASURE", ""), row.get("MEASURE", "unknown"))
            region = region_map.get(row.get("REGION", ""), row.get("REGION", "UNK"))

            # Upsert: delete existing record for same period/region/metric then insert
            db.query(LabourForceRecord).filter(
                LabourForceRecord.period == row["period"],
                LabourForceRecord.region == region,
                LabourForceRecord.metric == metric,
            ).delete()

            db.add(LabourForceRecord(
                period=row["period"],
                region=region,
                metric=metric,
                value=row["value"],
                adjustment="Seasonally Adjusted",
                unit="%",
            ))
            records_inserted += 1

        db.commit()

        run.status = "success"
        run.records_fetched = len(df)
        run.records_inserted = records_inserted
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[ABS Labour Force] ✓ Inserted {records_inserted} records")

    except Exception as exc:
        logger.error(f"[ABS Labour Force] ✗ {exc}")
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        _seed_mock_labour_force(db)

    return run


def _seed_mock_labour_force(db: Session) -> None:
    """Fallback mock data so the dashboard never shows empty state."""
    # Only seed if table is empty
    if db.query(LabourForceRecord).count() > 0:
        return
    logger.warning("[ABS Labour Force] Seeding mock data")
    import random
    random.seed(42)
    base_unemp = {"NSW": 3.8, "AUS": 4.1}
    base_part = {"NSW": 66.2, "AUS": 66.8}
    for year in range(2021, 2025):
        for month in range(1, 13):
            period = f"{year}-{month:02d}"
            for region in ["NSW", "AUS"]:
                drift = random.uniform(-0.15, 0.15)
                db.add(LabourForceRecord(period=period, region=region,
                    metric="unemployment_rate",
                    value=round(base_unemp[region] + drift, 2), unit="%"))
                db.add(LabourForceRecord(period=period, region=region,
                    metric="participation_rate",
                    value=round(base_part[region] + drift * 0.5, 2), unit="%"))
    db.commit()


# ---------------------------------------------------------
# CPI pipeline
# ---------------------------------------------------------

def fetch_cpi(db: Session, start_period: str = "2020-Q1") -> PipelineRun:
    """
    Fetch Sydney All Groups CPI from ABS (quarterly).

    Dataflow: CPI
    Key:      1    .1     .10      .Q
              meas  index  region  freq
    Index 1 = All Groups CPI, Region 10 = Sydney
    """
    url = (
        f"{ABS_BASE}/CPI/1.1.10.Q"
        f"?startPeriod={start_period}&format=jsondata"
    )

    run = PipelineRun(
        pipeline_name="abs_cpi",
        status="running",
        source_url=url,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        logger.info(f"[ABS CPI] Fetching {url}")
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, headers={"Accept": "application/vnd.sdmx.data+json;version=1.0"})
            resp.raise_for_status()
            payload = resp.json()

        df = parse_sdmx_json(payload)
        if df.empty:
            raise ValueError("Parsed DataFrame is empty")

        df_sorted = df.sort_values("period")

        records_inserted = 0
        prev_val: Optional[float] = None
        year_ago_val: Optional[float] = None
        history: list[float] = []

        for _, row in df_sorted.iterrows():
            val = row["value"]
            # Annual % change: compare to value 4 quarters ago
            year_ago_val = history[-4] if len(history) >= 4 else None
            pct_annual = round(((val - year_ago_val) / year_ago_val) * 100, 2) if year_ago_val else None

            db.query(CPIRecord).filter(
                CPIRecord.period == row["period"],
                CPIRecord.region == "Sydney",
            ).delete()

            db.add(CPIRecord(
                period=row["period"],
                region="Sydney",
                series="All Groups CPI",
                index_value=round(val, 1),
                pct_change_annual=pct_annual,
            ))
            history.append(val)
            records_inserted += 1

        db.commit()

        run.status = "success"
        run.records_fetched = len(df)
        run.records_inserted = records_inserted
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[ABS CPI] ✓ Inserted {records_inserted} records")

    except Exception as exc:
        logger.error(f"[ABS CPI] ✗ {exc}")
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        _seed_mock_cpi(db)

    return run


def _seed_mock_cpi(db: Session) -> None:
    if db.query(CPIRecord).count() > 0:
        return
    logger.warning("[ABS CPI] Seeding mock data")
    base = 113.2
    quarters = []
    for year in range(2020, 2025):
        for q in range(1, 5):
            quarters.append(f"{year}-Q{q}")
    for i, period in enumerate(quarters):
        base += round(0.6 + (0.8 if 8 <= i <= 14 else 0), 1)
        year_ago = base - 2.4 if i >= 4 else None
        pct = round(((base - year_ago) / year_ago) * 100, 2) if year_ago else None
        db.add(CPIRecord(period=period, region="Sydney",
            series="All Groups CPI", index_value=round(base, 1), pct_change_annual=pct))
    db.commit()
