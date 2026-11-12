"""CPI incremental YoY maths, building-approvals label filtering, crime CKAN ingestion."""

from app.models import BuildingApprovalRecord, CPIRecord, NSWCrimeRecord
from app.pipeline import abs_fetcher, common, nsw_fetcher
from tests.conftest import sdmx_payload


def stub(monkeypatch, payload):
    calls = []
    monkeypatch.setattr(common, "http_get_json", lambda url, **kw: (calls.append((url, kw)), payload)[1])
    return calls


def cpi_payload(periods, values):
    return sdmx_payload({"0": {str(i): v for i, v in enumerate(values)}}, {"INDEX": ["All groups"]}, periods)


def test_cpi_annual_change_survives_incremental_window(db, monkeypatch):
    quarters = ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2"]
    values = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    stub(monkeypatch, cpi_payload(quarters, values))
    abs_fetcher.fetch_cpi(db)
    q2 = db.query(CPIRecord).filter_by(period="2024-Q2").one()
    assert q2.pct_change_annual == 3.96           # 105 vs 101

    # New quarter arrives; the response window only has 2 quarters (year-ago values NOT in the payload)
    stub(monkeypatch, cpi_payload(["2024-Q2", "2024-Q3"], [105.0, 106.0]))
    run = abs_fetcher.fetch_cpi(db)
    assert run.records_inserted == 1 and run.records_updated == 0
    q3 = db.query(CPIRecord).filter_by(period="2024-Q3").one()
    assert q3.pct_change_annual == round((106 / 102 - 1) * 100, 2)      # uses stored 2023-Q3
    # earlier row's YoY must not have been wiped to NULL by the narrow window
    assert db.query(CPIRecord).filter_by(period="2024-Q2").one().pct_change_annual == 3.96


def test_building_approvals_filters_by_labels_and_prefers_original(db, monkeypatch):
    periods = ["2024-01", "2024-02", "2024-03"]
    series = {
        "0:0:0": {"0": 4500, "1": 4600, "2": 4700},     # NSW / total dwelling units / Original  ← wanted
        "0:0:1": {"0": 4400, "1": 4450, "2": 4500},     # NSW / total dwelling units / Seasonally adjusted
        "1:0:0": {"0": 3000, "1": 3100, "2": 3200},     # Victoria
        "0:1:0": {"0": 9e6, "1": 9e6, "2": 9e6},        # NSW / Value of dwellings ($'000)
    }
    payload = sdmx_payload(
        series,
        {"REGION": ["New South Wales", "Victoria"],
         "MEASURE": ["Total dwelling units approved", "Value of total dwelling units ($'000)"],
         "TSEST": ["Original", "Seasonally Adjusted"]},
        periods,
    )
    stub(monkeypatch, payload)
    run = abs_fetcher.fetch_building_approvals(db)
    assert run.status == "success" and run.mode == "live"
    rows = db.query(BuildingApprovalRecord).order_by(BuildingApprovalRecord.period).all()
    assert [r.value for r in rows] == [4500, 4600, 4700]


def test_building_approvals_no_match_falls_back_cleanly(db, monkeypatch):
    payload = sdmx_payload({"0": {"0": 1}}, {"REGION": ["Tasmania"]}, ["2024-01"])
    stub(monkeypatch, payload)
    run = abs_fetcher.fetch_building_approvals(db)
    assert run.status == "failed" and run.mode == "sample"
    assert db.query(BuildingApprovalRecord).filter_by(is_synthetic=True).count() > 12


def ckan_page(records):
    return {"success": True, "result": {"records": records}}


def test_crime_ingest_maps_columns_and_is_incremental(db, monkeypatch):
    def rec(year, lga, offence, n, rate):
        return {"Year": year, "LGA": f"{lga} (NSW)" if lga == "Bayside" else lga, "Offence": offence,
                "Incidents": f"{n:,}", "Rate": rate}

    records = [rec(y, lga, "Theft", 100 + y - 2019, 50.0)
               for y in range(2019, 2024) for lga in ("Sydney", "Bayside")]
    stub(monkeypatch, ckan_page(records))
    run = nsw_fetcher.fetch_nsw_crime(db)
    assert run.status == "success" and run.records_inserted == 10
    assert db.query(NSWCrimeRecord).filter_by(lga_name="Bayside").count() == 5       # "(NSW)" suffix stripped

    # Re-run, with the latest year revised and a new year added
    records2 = records + [rec(2024, "Sydney", "Theft", 130, 50.0), rec(2024, "Bayside", "Theft", 120, 50.0)]
    records2[-6]["Incidents"] = "999"       # 2023 Sydney revised
    stub(monkeypatch, ckan_page(records2))
    run2 = nsw_fetcher.fetch_nsw_crime(db)
    assert run2.records_inserted == 2 and run2.records_updated == 1
    assert run2.watermark == "2023"


def test_crime_unmappable_columns_is_audited(db, monkeypatch):
    stub(monkeypatch, ckan_page([{"foo": 1, "bar": 2}]))
    run = nsw_fetcher.fetch_nsw_crime(db)
    assert run.status == "failed" and "Cannot map crime columns" in run.error_message
