import pandas as pd

from app.pipeline.quality import Spec, period_index, shift_period, validate_frame

SPEC = Spec("test", group_cols=("region",), freq="M", min_value=0, max_value=100, min_points_for_outliers=8)


def frame(rows):
    return pd.DataFrame(rows, columns=["period", "region", "value"])


def months(n, start=2023 * 12):
    return [f"{(start + i) // 12}-{(start + i) % 12 + 1:02d}" for i in range(n)]


def test_clean_data_passes_untouched():
    df = frame([(p, "NSW", 4.0 + i * 0.01) for i, p in enumerate(months(12))])
    res = validate_frame(df, SPEC)
    assert len(res.df) == 12 and not res.issues and not res.rejected


def test_range_violations_dropped_as_errors():
    rows = [(p, "NSW", 4.0) for p in months(12)]
    rows[3] = (rows[3][0], "NSW", -5.0)
    rows[7] = (rows[7][0], "NSW", 450.0)
    res = validate_frame(frame(rows), SPEC)
    assert len(res.df) == 10
    assert res.dropped == 2
    assert {i.check for i in res.issues if i.severity == "error"} == {"range"}


def test_duplicates_collapsed_keep_last():
    rows = [(p, "NSW", 4.0) for p in months(10)] + [("2023-03", "NSW", 4.5)]
    res = validate_frame(frame(rows), SPEC)
    assert len(res.df) == 10
    assert res.df[res.df.period == "2023-03"]["value"].iloc[0] == 4.5
    assert any(i.check == "duplicate" for i in res.issues)


def test_outlier_flagged_but_kept():
    vals = [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.1, 4.0, 4.1, 3.9, 4.0, 40.0]
    res = validate_frame(frame([(p, "NSW", v) for p, v in zip(months(12), vals)]), SPEC)
    assert len(res.df) == 12                      # kept
    outliers = [i for i in res.issues if i.check == "outlier"]
    assert len(outliers) == 1 and outliers[0].severity == "warning" and outliers[0].value == 40.0


def test_missing_periods_reported_per_group():
    ms = months(12)
    rows = [(p, "NSW", 4.0) for p in ms if p not in ("2023-04", "2023-05")]
    res = validate_frame(frame(rows), SPEC)
    gap = [i for i in res.issues if i.check == "missing_period"]
    assert len(gap) == 1 and "2023-04" in gap[0].message and "2" in gap[0].message


def test_quality_gate_rejects_mostly_bad_load():
    rows = [(p, "NSW", 999.0) for p in months(10)]
    res = validate_frame(frame(rows), SPEC, max_drop_fraction=0.2)
    assert res.rejected and "gate" in res.reject_reason


def test_schema_failure_on_missing_columns_or_empty():
    assert validate_frame(pd.DataFrame(), SPEC).rejected
    assert validate_frame(pd.DataFrame({"period": ["2023-01"], "value": [1]}), SPEC).rejected


def test_period_helpers():
    assert period_index("2024-03", "M") == 2024 * 12 + 2
    assert shift_period("2024-01", "M", -3) == "2023-10"
    assert shift_period("2024-Q1", "Q", -6) == "2022-Q3"
    assert shift_period("2020", "A", -1) == "2019"
