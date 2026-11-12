import os
import tempfile

# Configure BEFORE the app is imported: temp SQLite file, no background work.
_tmp = tempfile.mkdtemp(prefix="bi-test-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "")
os.environ["RUN_PIPELINES_ON_STARTUP"] = "off"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["API_KEY"] = ""

# A fake built frontend so the single-container static-serving path is exercised too.
_static = os.path.join(_tmp, "static")
os.makedirs(os.path.join(_static, "assets"), exist_ok=True)
with open(os.path.join(_static, "index.html"), "w") as f:
    f.write('<!doctype html><div id="root"></div>')
with open(os.path.join(_static, "assets", "app.js"), "w") as f:
    f.write("console.log('app')")
with open(os.path.join(_tmp, "secret.txt"), "w") as f:       # outside STATIC_DIR — must never be served
    f.write("TOP-SECRET")
os.environ["STATIC_DIR"] = _static

import pytest  # noqa: E402

from app import cache  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache.clear()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def sdmx_payload(series: dict[str, dict[str, float]], dims: dict[str, list[str]], periods: list[str]) -> dict:
    """
    Build a minimal ABS-style SDMX-JSON payload.
    series: {"0:0": {"0": 3.9, "1": 4.0}}  (series key -> {time index -> value})
    dims:   {"MEASURE": ["Unemployment rate", ...], "REGION": [...]}
    """
    return {
        "data": {
            "structure": {"dimensions": {
                "series": [{"id": k, "values": [{"id": str(i), "name": n} for i, n in enumerate(v)]}
                           for k, v in dims.items()],
                "observation": [{"id": "TIME_PERIOD", "values": [{"id": p} for p in periods]}],
            }},
            "dataSets": [{"series": {k: {"observations": {t: [v] for t, v in obs.items()}}
                                     for k, obs in series.items()}}],
        }
    }


def labour_payload(periods: list[str], nsw: list[float], aus: list[float]) -> dict:
    n = len(periods)
    return sdmx_payload(
        series={
            "0:0": {str(i): nsw[i] for i in range(n)},
            "0:1": {str(i): aus[i] for i in range(n)},
        },
        dims={"MEASURE": ["Unemployment rate"], "REGION": ["New South Wales", "Australia"]},
        periods=periods,
    )
