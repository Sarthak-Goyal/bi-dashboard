from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint, false,
)
from sqlalchemy.sql import func

from app.database import Base


class _Provenance:
    """Columns shared by every data table."""
    is_synthetic = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LabourForceRecord(_Provenance, Base):
    """ABS Labour Force data — unemployment rate, participation rate."""
    __tablename__ = "labour_force"
    __table_args__ = (UniqueConstraint("period", "region", "metric", name="uq_labour_key"),)

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(10), index=True, nullable=False)       # "2024-03"
    region = Column(String(50), nullable=False)                    # "NSW" | "AUS"
    metric = Column(String(100), nullable=False)                   # unemployment_rate | participation_rate
    value = Column(Float, nullable=False)
    adjustment = Column(String(50), default="Seasonally Adjusted")
    unit = Column(String(20), default="%")


class CPIRecord(_Provenance, Base):
    """ABS Consumer Price Index — Sydney quarterly."""
    __tablename__ = "cpi"
    __table_args__ = (UniqueConstraint("period", "region", "series", name="uq_cpi_key"),)

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(10), index=True, nullable=False)        # "2024-Q1"
    region = Column(String(50), nullable=False)
    series = Column(String(200), nullable=False)
    index_value = Column(Float, nullable=False)
    pct_change_annual = Column(Float, nullable=True)


class BuildingApprovalRecord(_Provenance, Base):
    """ABS Building Approvals — NSW dwelling units approved, monthly."""
    __tablename__ = "building_approvals"
    __table_args__ = (UniqueConstraint("period", "region", "building_type", name="uq_ba_key"),)

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(10), index=True, nullable=False)        # "2024-03"
    region = Column(String(50), nullable=False)                    # "NSW"
    building_type = Column(String(100), nullable=False)            # "Total dwelling units"
    value = Column(Float, nullable=False)
    unit = Column(String(20), default="dwellings")


class NSWCrimeRecord(_Provenance, Base):
    """NSW Open Data — recorded crime by LGA."""
    __tablename__ = "nsw_crime"
    __table_args__ = (UniqueConstraint("year", "lga_name", "offence_category", name="uq_crime_key"),)

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True, nullable=False)
    lga_name = Column(String(100), nullable=False, index=True)
    offence_category = Column(String(200), nullable=False)
    incidents_recorded = Column(Integer, nullable=False)
    rate_per_100k = Column(Float, nullable=True)


class PipelineRun(Base):
    """Audit log for every ETL pipeline execution."""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)                    # running | success | failed
    mode = Column(String(10), nullable=True)                       # live | sample
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)                   # dropped by quality checks
    quality_issues = Column(Integer, default=0)
    watermark = Column(String(20), nullable=True)                  # latest period loaded before this run
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)


class DataQualityIssue(Base):
    """One row per problem found by the validation layer."""
    __tablename__ = "data_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, index=True, nullable=True)
    pipeline_name = Column(String(100), nullable=False, index=True)
    severity = Column(String(10), nullable=False)                  # error (row dropped) | warning (kept)
    check = Column(String(30), nullable=False)                     # schema | range | outlier | missing_period | duplicate
    key = Column(String(200), nullable=True)                       # e.g. "NSW / unemployment_rate / 2023-04"
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
