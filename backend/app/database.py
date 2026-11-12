import logging
import time

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _normalise_url(url: str) -> str:
    """Accept the URL styles hosting providers hand out and make them SQLAlchemy-friendly."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


if settings.database_url:
    DATABASE_URL = _normalise_url(settings.database_url)
else:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{settings.data_dir.as_posix()}/dashboard.db"

IS_SQLITE = DATABASE_URL.startswith("sqlite")
DIALECT = "sqlite" if IS_SQLITE else DATABASE_URL.split(":", 1)[0].split("+", 1)[0]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(retries: int = 15, delay: float = 2.0) -> None:
    """Hosted databases often come up a few seconds after the app container — retry instead of crashing."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect():
                return
        except OperationalError as exc:
            if attempt == retries:
                raise
            logger.warning("Database not ready (attempt %d/%d): %s", attempt, retries, str(exc).splitlines()[0][:120])
            time.sleep(delay)


def init_db() -> None:
    """
    Create tables. This project stores *derived, re-fetchable* data, so if an
    older SQLite file from v1 is found (missing the new columns) it is rebuilt
    rather than migrated. On other databases we only warn.
    """
    from app import models  # noqa: F401  (register tables)

    wait_for_db()

    insp = inspect(engine)
    if insp.has_table("labour_force"):
        cols = {c["name"] for c in insp.get_columns("labour_force")}
        if "is_synthetic" not in cols:
            if IS_SQLITE:
                logger.warning("Old database schema detected — rebuilding (data is re-fetched).")
                Base.metadata.drop_all(bind=engine)
            else:
                logger.error("Database schema is out of date. Drop the tables and restart.")
    Base.metadata.create_all(bind=engine)
