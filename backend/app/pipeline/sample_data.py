"""
Synthetic sample data.

Used ONLY when a live source cannot be reached (offline demo, API outage,
upstream schema change). Every row is stored with is_synthetic=True, the API
reports `data_mode: "sample"`, and the UI shows a banner — so sample numbers
are never presented as real statistics. Generation is deterministic.
"""

import json
import math
import random
from datetime import date
from pathlib import Path

from app.pipeline.quality import index_to_period, period_index

OFFENCES = [
    "Theft", "Assault (non-domestic)", "Drug offences",
    "Property damage", "Break and enter", "Motor vehicle theft",
]
# Rough per-100k annual rates used to shape the sample numbers (illustrative only)
_OFFENCE_RATE = {
    "Theft": 1500, "Assault (non-domestic)": 330, "Drug offences": 650,
    "Property damage": 700, "Break and enter": 330, "Motor vehicle theft": 140,
}
# Approximate populations for the largest councils; others are generated.
_KNOWN_POP = {
    "Blacktown": 420_000, "Canterbury-Bankstown": 380_000, "Central Coast": 345_000,
    "Sydney": 250_000, "Northern Beaches": 265_000, "Parramatta": 260_000,
    "Liverpool": 235_000, "Sutherland Shire": 230_000, "Penrith": 220_000,
    "Campbelltown": 180_000, "Newcastle": 170_000, "Lake Macquarie": 215_000,
    "Wollongong": 220_000, "Fairfield": 210_000, "Cumberland": 245_000,
    "Georges River": 150_000, "Bayside": 180_000, "Inner West": 185_000,
    "Randwick": 155_000, "The Hills Shire": 190_000,
}

_LGA_FILE = Path(__file__).resolve().parents[1] / "data" / "lga_names.json"


def lga_names() -> list[str]:
    return json.loads(_LGA_FILE.read_text())


def _today() -> date:
    return date.today()


def latest_month() -> str:
    """ABS monthly releases lag ~2 months."""
    t = _today()
    return index_to_period(t.year * 12 + t.month - 1 - 2, "M")


def latest_quarter() -> str:
    t = _today()
    q_idx = t.year * 4 + (t.month - 1) // 3
    return index_to_period(q_idx - 2, "Q")      # last published quarter ≈ 2 behind


def _range(start: str, end: str, freq: str) -> list[str]:
    a, b = period_index(start, freq), period_index(end, freq)
    return [index_to_period(i, freq) for i in range(a, b + 1)]


def sample_labour_force() -> list[dict]:
    rng = random.Random(42)
    rows = []
    base_u = {"NSW": 3.7, "AUS": 4.0}
    base_p = {"NSW": 65.8, "AUS": 66.6}
    for i, period in enumerate(_range("2021-01", latest_month(), "M")):
        wave = math.sin(i / 9)
        for region in ("NSW", "AUS"):
            u = base_u[region] + 0.35 * wave + rng.uniform(-0.1, 0.1) + (0.4 if i < 12 else 0)
            p = base_p[region] + 0.3 * math.cos(i / 11) + rng.uniform(-0.12, 0.12)
            rows.append(dict(period=period, region=region, metric="unemployment_rate",
                             value=round(u, 2), adjustment="Seasonally Adjusted", unit="%"))
            rows.append(dict(period=period, region=region, metric="participation_rate",
                             value=round(p, 2), adjustment="Seasonally Adjusted", unit="%"))
    return rows


def sample_cpi() -> list[dict]:
    index, rows, history = 113.2, [], []
    quarterly_growth = {2020: 0.4, 2021: 0.8, 2022: 1.7, 2023: 1.0, 2024: 0.7}
    for period in _range("2020-Q1", latest_quarter(), "Q"):
        year = int(period[:4])
        index *= 1 + quarterly_growth.get(year, 0.65) / 100
        history.append(index)
        yoy = round((index / history[-5] - 1) * 100, 2) if len(history) >= 5 else None
        rows.append(dict(period=period, region="Sydney", series="All Groups CPI",
                         index_value=round(index, 1), pct_change_annual=yoy))
    return rows


def sample_building_approvals() -> list[dict]:
    rng = random.Random(7)
    level, rows = 4600.0, []
    for i, period in enumerate(_range("2021-01", latest_month(), "M")):
        level += (4400 - level) * 0.08 + rng.uniform(-170, 170)       # mean-reverting walk
        seasonal = 1 + 0.07 * math.sin((i % 12) / 12 * 2 * math.pi)
        rows.append(dict(period=period, region="NSW", building_type="Total dwelling units",
                         value=float(round(level * seasonal)), unit="dwellings"))
    return rows


def sample_crime() -> list[dict]:
    names = lga_names()
    rng = random.Random(99)
    last_year = _today().year - 1
    rows = []
    for lga in names:
        local = random.Random(lga)                 # stable per-LGA characteristics
        pop = _KNOWN_POP.get(lga) or int(local.lognormvariate(9.6, 0.9))
        pop = max(1_500, min(pop, 300_000))
        factor = 3.0 if lga == "Sydney" else local.uniform(0.6, 1.6)
        for year in range(2019, last_year + 1):
            trend = 1 + 0.012 * (year - 2019) + (-0.10 if year == 2020 else 0)
            for offence in OFFENCES:
                expected = pop / 100_000 * _OFFENCE_RATE[offence] * factor * trend
                incidents = max(0, int(expected * rng.uniform(0.85, 1.15)))
                rows.append(dict(
                    year=year, lga_name=lga, offence_category=offence,
                    incidents_recorded=incidents,
                    rate_per_100k=round(incidents / pop * 100_000, 1),
                ))
    return rows
