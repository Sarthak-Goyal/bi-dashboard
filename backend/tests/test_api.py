import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.pipeline import abs_fetcher, nsw_fetcher, common
from app.pipeline.abs_fetcher import fetch_building_approvals, fetch_cpi, fetch_labour_force
from app.pipeline.nsw_fetcher import fetch_nsw_crime


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded(db, monkeypatch):
    """Populate every dataset with sample data by simulating an offline start."""
    monkeypatch.setattr(common, "http_get_json", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("offline")))
    for fn in (fetch_labour_force, fetch_cpi, fetch_building_approvals, fetch_nsw_crime):
        fn(db)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_summary_shape_and_sample_label(client, seeded):
    body = client.get("/api/metrics/summary").json()
    assert body["data_mode"]["overall"] == "sample"
    assert set(body["data_mode"]["sample_datasets"]) == {"labour_force", "cpi", "building_approvals", "crime"}
    for k in ("unemployment_rate", "participation_rate", "cpi_annual_change", "building_approvals", "crime_incidents"):
        assert body[k]["value"] is not None, k


def test_summary_is_cached_then_invalidated_by_pipeline_run(client, seeded, db):
    assert client.get("/api/metrics/summary").headers["X-Cache"] == "MISS"
    assert client.get("/api/metrics/summary").headers["X-Cache"] == "HIT"
    fetch_labour_force(db)                                   # any pipeline run clears the cache
    assert client.get("/api/metrics/summary").headers["X-Cache"] == "MISS"


def test_range_parameters(client, seeded):
    assert len(client.get("/api/metrics/unemployment/compare?months=12").json()["series"]) == 12
    all_ = client.get("/api/metrics/unemployment/compare?months=0").json()["series"]
    assert len(all_) > 36
    assert len(client.get("/api/metrics/cpi?quarters=8").json()["series"]) == 8
    assert len(client.get("/api/metrics/cpi?quarters=0").json()["series"]) > 8
    trend = client.get("/api/metrics/crime/trend?offence=Theft&years=3").json()
    assert len(trend["series"]) == 3


def test_history_pagination(client, seeded):
    p1 = client.get("/api/pipeline/history?page=1&page_size=3").json()
    assert p1["total"] >= 4 and len(p1["runs"]) == 3 and p1["pages"] >= 2
    p2 = client.get("/api/pipeline/history?page=2&page_size=3").json()
    assert {r["id"] for r in p1["runs"]}.isdisjoint({r["id"] for r in p2["runs"]})


def test_records_endpoint_paginates_and_validates(client, seeded):
    r = client.get("/api/metrics/records/crime?page=2&page_size=100").json()
    assert r["page"] == 2 and len(r["items"]) == 100 and r["total"] > 1000
    assert client.get("/api/metrics/records/nope").status_code == 404
    assert client.get("/api/metrics/records/crime?page_size=9999").status_code == 422


def test_multi_source_join(client, seeded):
    body = client.get("/api/metrics/housing-labour?months=24").json()
    assert len(body["series"]) == 24
    row = body["series"][-1]
    assert {"approvals", "unemployment_rate", "approvals_3m_avg", "cpi_annual"} <= row.keys()
    assert body["stats"]["n"] > 24 and -1 <= body["stats"]["correlation"] <= 1


def test_crime_by_lga_covers_all_councils(client, seeded):
    body = client.get("/api/metrics/crime/by-lga").json()
    assert len(body["series"]) == 129
    assert all(r["rate_per_100k"] is not None for r in body["series"])
    theft = client.get("/api/metrics/crime/by-lga?offence=Theft").json()
    assert sum(r["incidents"] for r in theft["series"]) < sum(r["incidents"] for r in body["series"])


def test_refresh_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "s3cret")
    assert client.post("/api/pipeline/refresh?pipeline=abs_cpi").status_code == 401
    assert client.post("/api/pipeline/refresh?pipeline=abs_cpi", headers={"X-API-Key": "wrong"}).status_code == 401
    ok = client.post("/api/pipeline/refresh?pipeline=abs_cpi", headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200
    # read endpoints stay open
    assert client.get("/api/pipeline/status").status_code == 200


def test_refresh_open_in_dev_and_rejects_unknown_pipeline(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "")
    assert client.post("/api/pipeline/refresh?pipeline=bogus").status_code == 400
