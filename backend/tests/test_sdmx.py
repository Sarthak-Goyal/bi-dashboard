import pytest

from app.pipeline.sdmx import SdmxSchemaError, parse_sdmx_json
from tests.conftest import labour_payload


def test_parses_valid_payload():
    df = parse_sdmx_json(labour_payload(["2024-01", "2024-02"], [3.9, 4.0], [4.1, 4.2]))
    assert len(df) == 4
    assert set(df["REGION"]) == {"New South Wales", "Australia"}
    assert df[(df.REGION == "New South Wales") & (df.period == "2024-02")]["value"].iloc[0] == 4.0


def test_skips_null_and_non_numeric_observations():
    payload = labour_payload(["2024-01", "2024-02"], [3.9, 4.0], [4.1, 4.2])
    payload["data"]["dataSets"][0]["series"]["0:0"]["observations"]["1"] = [None]
    payload["data"]["dataSets"][0]["series"]["0:1"]["observations"]["1"] = ["n/a"]
    df = parse_sdmx_json(payload)
    assert len(df) == 2


@pytest.mark.parametrize("bad", [
    {},                                              # nothing
    {"data": {}},                                    # no structure
    {"data": {"structure": {"dimensions": {}}, "dataSets": []}},   # no datasets
    {"error": "rate limited"},
    "<html>maintenance</html>",
])
def test_schema_changes_raise_clear_error(bad):
    with pytest.raises(SdmxSchemaError):
        parse_sdmx_json(bad)
