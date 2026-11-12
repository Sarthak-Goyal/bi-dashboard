"""Pipeline behaviour: fallback, labelling, incremental loads, quality gate."""

from app.models import DataQualityIssue, LabourForceRecord, PipelineRun
from app.pipeline import abs_fetcher, common
from app.routers.metrics import data_mode
from tests.conftest import labour_payload

PERIODS = [f"2024-{m:02d}" for m in range(1, 13)]
NSW = [3.8, 3.9, 3.9, 4.0, 4.0, 4.1, 4.0, 3.9, 3.9, 4.0, 4.1, 4.1]
AUS = [4.0, 4.1, 4.1, 4.2, 4.2, 4.3, 4.2, 4.1, 4.1, 4.2, 4.3, 4.3]


def stub_http(monkeypatch, payload=None, error=None):
    calls = []

    def fake(url, **kw):
        calls.append(url)
        if error:
            raise error
        return payload

    monkeypatch.setattr(common, "http_get_json", fake)
    return calls


def test_offline_falls_back_to_labelled_sample_data(db, monkeypatch):
    stub_http(monkeypatch, error=ConnectionError("no network"))
    run = abs_fetcher.fetch_labour_force(db)
    assert run.status == "failed" and run.mode == "sample"
    assert "ConnectionError" in run.error_message
    rows = db.query(LabourForceRecord).all()
    assert rows and all(r.is_synthetic for r in rows)
    assert data_mode(db)["datasets"]["labour_force"] == "sample"


def test_live_load_replaces_sample_data(db, monkeypatch):
    stub_http(monkeypatch, error=ConnectionError("down"))
    abs_fetcher.fetch_labour_force(db)                       # seeds sample rows
    stub_http(monkeypatch, labour_payload(PERIODS, NSW, AUS))
    run = abs_fetcher.fetch_labour_force(db)
    assert run.status == "success" and run.mode == "live"
    rows = db.query(LabourForceRecord).all()
    assert len(rows) == 24 and not any(r.is_synthetic for r in rows)
    assert data_mode(db)["datasets"]["labour_force"] == "live"


def test_second_identical_run_is_a_noop(db, monkeypatch):
    stub_http(monkeypatch, labour_payload(PERIODS, NSW, AUS))
    first = abs_fetcher.fetch_labour_force(db)
    assert first.records_inserted == 24
    second = abs_fetcher.fetch_labour_force(db)
    assert (second.records_inserted, second.records_updated) == (0, 0)
    assert db.query(LabourForceRecord).count() == 24


def test_incremental_uses_watermark_and_applies_revisions(db, monkeypatch):
    stub_http(monkeypatch, labour_payload(PERIODS, NSW, AUS))
    abs_fetcher.fetch_labour_force(db)

    # Next run: ABS revised Nov (-> 4.3) and published Jan 2025. Request must start near the watermark.
    periods = ["2024-10", "2024-11", "2024-12", "2025-01"]
    calls = stub_http(monkeypatch, labour_payload(periods, [4.0, 4.3, 4.1, 4.2], [4.2, 4.4, 4.3, 4.3]))
    run = abs_fetcher.fetch_labour_force(db)

    assert "startPeriod=2024-09" in calls[0]            # watermark 2024-12 minus 3 months — not the full history
    assert run.watermark == "2024-12"
    assert run.records_inserted == 2                    # Jan 2025 for NSW + AUS
    assert run.records_updated == 2                     # Nov revised for NSW + AUS
    nov = db.query(LabourForceRecord).filter_by(period="2024-11", region="NSW").one()
    assert nov.value == 4.3


def test_bad_feed_is_rejected_and_existing_data_kept(db, monkeypatch):
    stub_http(monkeypatch, labour_payload(PERIODS, NSW, AUS))
    abs_fetcher.fetch_labour_force(db)
    before = {(r.period, r.region): r.value for r in db.query(LabourForceRecord)}

    garbage = [999.0] * 4                               # impossible rates → quality gate
    stub_http(monkeypatch, labour_payload(PERIODS[-4:], garbage, garbage))
    run = abs_fetcher.fetch_labour_force(db)

    assert run.status == "failed" and "gate" in run.error_message
    assert {(r.period, r.region): r.value for r in db.query(LabourForceRecord)} == before
    assert db.query(DataQualityIssue).filter_by(check="range").count() > 0


def test_schema_change_is_audited_not_crashing(db, monkeypatch):
    stub_http(monkeypatch, {"unexpected": "shape"})
    run = abs_fetcher.fetch_labour_force(db)
    assert run.status == "failed" and "SdmxSchemaError" in run.error_message
    assert db.query(PipelineRun).count() == 1
