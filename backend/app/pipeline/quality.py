"""
Data-quality validation layer.

Runs *before* anything is written to the database. Each check either
  - drops the row and records an `error` issue (impossible / duplicate values), or
  - keeps the row and records a `warning` issue (suspicious but plausible).

Checks: schema · duplicates · range · outliers (robust z-score) · missing periods.
If too large a fraction of rows is dropped the whole load is rejected
(a "quality gate"), so a broken upstream feed can never overwrite good data.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import DataQualityIssue


@dataclass
class Issue:
    severity: str          # "error" | "warning"
    check: str             # schema | duplicate | range | outlier | missing_period
    dataset: str
    key: str
    message: str
    value: Optional[float] = None


@dataclass
class Spec:
    dataset: str
    value_col: str = "value"
    period_col: str = "period"
    group_cols: tuple[str, ...] = ()
    freq: str = "M"                         # M monthly | Q quarterly | A annual
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    outlier_z: float = 6.0                  # modified z-score threshold
    min_points_for_outliers: int = 8
    required_cols: tuple[str, ...] = ()


@dataclass
class QualityResult:
    df: pd.DataFrame
    issues: list[Issue] = field(default_factory=list)
    dropped: int = 0
    rejected: bool = False
    reject_reason: str = ""

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# ── period helpers ───────────────────────────────────────────────────────────

def period_index(period: str, freq: str) -> Optional[int]:
    """Map a period label to a monotonically increasing integer (for gap detection)."""
    try:
        if freq == "M":
            y, m = str(period).split("-")
            return int(y) * 12 + int(m) - 1
        if freq == "Q":
            y, q = str(period).split("-Q")
            return int(y) * 4 + int(q) - 1
        if freq == "A":
            return int(period)
    except (ValueError, AttributeError):
        return None
    return None


def index_to_period(idx: int, freq: str) -> str:
    if freq == "M":
        return f"{idx // 12}-{idx % 12 + 1:02d}"
    if freq == "Q":
        return f"{idx // 4}-Q{idx % 4 + 1}"
    return str(idx)


def shift_period(period: str, freq: str, n: int) -> str:
    idx = period_index(period, freq)
    if idx is None:
        return period
    return index_to_period(idx + n, freq)


# ── validation ───────────────────────────────────────────────────────────────

def validate_frame(df: pd.DataFrame, spec: Spec, max_drop_fraction: float = 0.2) -> QualityResult:
    issues: list[Issue] = []
    ds = spec.dataset

    # 1. Schema ---------------------------------------------------------------
    needed = {spec.period_col, spec.value_col, *spec.group_cols, *spec.required_cols}
    missing = needed - set(df.columns)
    if df.empty or missing:
        reason = (f"missing columns {sorted(missing)}" if missing else "no rows returned")
        issues.append(Issue("error", "schema", ds, "-", f"Schema check failed: {reason}"))
        return QualityResult(df.iloc[0:0], issues, dropped=len(df), rejected=True, reject_reason=reason)

    work = df.copy()
    total = len(work)

    def label(row) -> str:
        parts = [str(row[c]) for c in spec.group_cols] + [str(row[spec.period_col])]
        return " / ".join(parts)

    # 2. Numeric coercion -------------------------------------------------------
    work[spec.value_col] = pd.to_numeric(work[spec.value_col], errors="coerce")
    bad = work[spec.value_col].isna()
    for _, row in work[bad].head(20).iterrows():
        issues.append(Issue("error", "schema", ds, label(row), "Value is not numeric"))
    work = work[~bad]

    # 3. Duplicates -------------------------------------------------------------
    key_cols = [*spec.group_cols, spec.period_col]
    dup = work.duplicated(subset=key_cols, keep="last")
    for _, row in work[dup].head(20).iterrows():
        issues.append(Issue("error", "duplicate", ds, label(row), "Duplicate key in feed — last value kept",
                            float(row[spec.value_col])))
    work = work[~dup]

    # 4. Range -------------------------------------------------------------------
    out_of_range = pd.Series(False, index=work.index)
    if spec.min_value is not None:
        out_of_range |= work[spec.value_col] < spec.min_value
    if spec.max_value is not None:
        out_of_range |= work[spec.value_col] > spec.max_value
    for _, row in work[out_of_range].head(20).iterrows():
        issues.append(Issue(
            "error", "range", ds, label(row),
            f"Value {row[spec.value_col]:g} outside plausible range "
            f"[{spec.min_value}, {spec.max_value}] — row dropped",
            float(row[spec.value_col]),
        ))
    work = work[~out_of_range]

    # 5. Outliers (kept, flagged) -------------------------------------------------
    groups = work.groupby(list(spec.group_cols)) if spec.group_cols else [((), work)]
    for gkey, g in groups:
        if len(g) < spec.min_points_for_outliers:
            continue
        vals = g[spec.value_col].to_numpy(dtype=float)
        med = np.median(vals)
        mad = np.median(np.abs(vals - med))
        if mad == 0:
            continue
        mz = 0.6745 * (vals - med) / mad
        for pos in np.where(np.abs(mz) > spec.outlier_z)[0][:5]:
            row = g.iloc[pos]
            issues.append(Issue(
                "warning", "outlier", ds, label(row),
                f"Value {vals[pos]:g} is unusual for this series (median {med:.4g}, modified z={mz[pos]:.1f})",
                float(vals[pos]),
            ))

    # 6. Missing periods (flagged) --------------------------------------------------
    groups = work.groupby(list(spec.group_cols)) if spec.group_cols else [((), work)]
    for gkey, g in groups:
        idxs = sorted({i for i in (period_index(p, spec.freq) for p in g[spec.period_col]) if i is not None})
        if len(idxs) < 2:
            continue
        gaps = sorted(set(range(idxs[0], idxs[-1] + 1)) - set(idxs))
        if gaps:
            names = ", ".join(index_to_period(i, spec.freq) for i in gaps[:6])
            more = f" (+{len(gaps) - 6} more)" if len(gaps) > 6 else ""
            gname = " / ".join(str(x) for x in (gkey if isinstance(gkey, tuple) else (gkey,))) or ds
            issues.append(Issue("warning", "missing_period", ds, gname,
                                f"{len(gaps)} missing period(s): {names}{more}"))

    dropped = total - len(work)
    result = QualityResult(work.reset_index(drop=True), issues, dropped=dropped)

    # Quality gate
    if total and dropped / total > max_drop_fraction:
        result.rejected = True
        result.reject_reason = (f"{dropped}/{total} rows ({dropped / total:.0%}) failed validation "
                                f"— above the {max_drop_fraction:.0%} gate")
    return result


def record_issues(db: Session, pipeline_name: str, run_id: Optional[int], issues: list[Issue], cap: int = 200) -> int:
    for i in issues[:cap]:
        db.add(DataQualityIssue(
            run_id=run_id, pipeline_name=pipeline_name, severity=i.severity, check=i.check,
            key=i.key[:200], message=i.message, value=i.value,
        ))
    db.commit()
    return min(len(issues), cap)
