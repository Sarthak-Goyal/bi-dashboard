from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class LabourForceRecord(Base):
    """ABS Labour Force data — unemployment rate, participation rate, etc."""
    __tablename__ = "labour_force"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(10), index=True, nullable=False)       # e.g. "2024-03"
    region = Column(String(50), nullable=False)                    # "NSW" | "AUS"
    metric = Column(String(100), nullable=False)                   # "unemployment_rate" | "participation_rate"
    value = Column(Float, nullable=False)
    adjustment = Column(String(50), default="Seasonally Adjusted")
    unit = Column(String(20), default="%")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CPIRecord(Base):
    """ABS Consumer Price Index — Sydney quarterly."""
    __tablename__ = "cpi"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(10), index=True, nullable=False)        # e.g. "2024-Q1"
    region = Column(String(50), nullable=False)                    # "Sydney"
    series = Column(String(200), nullable=False)                   # "All Groups CPI"
    index_value = Column(Float, nullable=False)
    pct_change_annual = Column(Float, nullable=True)               # YoY %
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NSWCrimeRecord(Base):
    """NSW Open Data — crime statistics by LGA."""
    __tablename__ = "nsw_crime"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True, nullable=False)
    lga_name = Column(String(100), nullable=False)
    offence_category = Column(String(200), nullable=False)
    incidents_recorded = Column(Integer, nullable=False)
    rate_per_100k = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PipelineRun(Base):
    """Audit log for every ETL pipeline execution."""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)                    # "success" | "failed" | "running"
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
