"""
SDMX-JSON parsing with schema validation.

The ABS API returns SDMX-JSON. Instead of trusting dictionary lookups (which
raise cryptic KeyErrors when the response shape changes), the payload is first
validated against Pydantic models. A shape change then produces one clear
`SdmxSchemaError`, which the pipeline logs and handles (fallback + audit log).
"""

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class SdmxSchemaError(ValueError):
    """The response did not look like SDMX-JSON data."""


class _Value(BaseModel):
    id: str
    name: str | None = None


class _Dimension(BaseModel):
    id: str
    values: list[_Value] = Field(default_factory=list)


class _Dimensions(BaseModel):
    series: list[_Dimension] = Field(default_factory=list)
    observation: list[_Dimension] = Field(default_factory=list)


class _Structure(BaseModel):
    dimensions: _Dimensions


class _Series(BaseModel):
    observations: dict[str, list[Any]] = Field(default_factory=dict)


class _DataSet(BaseModel):
    series: dict[str, _Series] = Field(default_factory=dict)


class _Data(BaseModel):
    structure: _Structure
    dataSets: list[_DataSet] = Field(min_length=1)


class SdmxPayload(BaseModel):
    data: _Data


def validate_payload(payload: Any) -> SdmxPayload:
    try:
        return SdmxPayload.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise SdmxSchemaError(
            f"Unexpected SDMX response shape at '{where}': {first['msg']} "
            f"({exc.error_count()} problem(s))"
        ) from exc


def parse_sdmx_json(payload: Any) -> pd.DataFrame:
    """
    Convert an ABS SDMX-JSON response into a tidy DataFrame with one column per
    series dimension (labelled by name), plus `period` and `value`.
    """
    model = validate_payload(payload)
    structure = model.data.structure
    dataset = model.data.dataSets[0]

    obs_dims = structure.dimensions.observation
    if not obs_dims:
        raise SdmxSchemaError("Response has no observation (time) dimension")
    time_dim = next((d for d in obs_dims if d.id in ("TIME_PERIOD", "TIME")), obs_dims[0])
    periods = [v.id for v in time_dim.values]

    series_dims = structure.dimensions.series
    rows: list[dict] = []
    for series_key, series in dataset.series.items():
        try:
            idx_parts = [int(i) for i in series_key.split(":")]
        except ValueError as exc:
            raise SdmxSchemaError(f"Malformed series key '{series_key}'") from exc

        labels: dict[str, str] = {}
        for i, dim in enumerate(series_dims):
            try:
                v = dim.values[idx_parts[i]]
                labels[dim.id] = v.name or v.id
            except IndexError:
                labels[dim.id] = str(idx_parts[i]) if i < len(idx_parts) else ""

        for t_str, obs in series.observations.items():
            try:
                t_idx = int(t_str)
            except ValueError:
                continue
            value = obs[0] if obs else None
            if value is None or t_idx >= len(periods):
                continue
            try:
                rows.append({**labels, "period": periods[t_idx], "value": float(value)})
            except (TypeError, ValueError):
                continue  # non-numeric observation; the quality layer reports on what remains

    return pd.DataFrame(rows)
