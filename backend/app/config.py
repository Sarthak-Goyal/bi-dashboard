"""
Central configuration — every setting can be overridden with an environment
variable (or a .env file in the backend/ folder). See .env.example.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── General ───────────────────────────────────────────────────────────
    environment: str = "development"          # development | production

    # ── Database ──────────────────────────────────────────────────────────
    # Leave DATABASE_URL empty to use SQLite in DATA_DIR.
    # For Postgres set e.g. postgresql://user:pass@host:5432/dbname
    database_url: str = ""
    data_dir: Path = BACKEND_DIR / "data"

    # ── Security ──────────────────────────────────────────────────────────
    # If set, write endpoints (POST /api/pipeline/refresh) require the header
    # `X-API-Key: <value>`. If empty, they are open (local development only).
    api_key: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Serving the built frontend from this process (single-container deploy)
    static_dir: str = ""

    # ── Pipelines ─────────────────────────────────────────────────────────
    run_pipelines_on_startup: str = "background"   # background | sync | off
    enable_scheduler: bool = True
    full_refresh_hours: int = 6
    labour_refresh_hours: int = 1
    http_timeout: float = 30.0
    abs_base_url: str = "https://api.data.abs.gov.au/data"
    ckan_base_url: str = "https://data.nsw.gov.au/data/api/3/action"
    crime_resource_id: str = "f52d9f86-9d7e-4614-b7db-7b4c45d5a0cc"
    # Fraction of rows a quality gate may drop before the whole load is rejected
    quality_max_drop_fraction: float = 0.2

    # ── API cache ─────────────────────────────────────────────────────────
    cache_ttl_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
