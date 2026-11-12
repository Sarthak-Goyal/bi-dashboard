"""
Local stand-in for the ABS SDMX API and NSW Open Data (CKAN) — for demos and offline development.

It serves *generated* data with deliberate problems injected (a missing month, an outlier, an
impossible value, extra rows from other states) so you can watch the dashboard's incremental loads
and data-quality layer work without internet access. The numbers are NOT real statistics.

  Terminal 1:  python scripts/demo_upstream.py
  Terminal 2:  ABS_BASE_URL=http://127.0.0.1:9000/data CKAN_BASE_URL=http://127.0.0.1:9000/ckan \
               RUN_PIPELINES_ON_STARTUP=sync uvicorn app.main:app
  Publish a new month + revision:  curl http://127.0.0.1:9000/__advance   then Refresh All in the UI
"""

import argparse
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

STATE = {"advanced": False}


def months(start_year: int, n: int) -> list[str]:
    return [f"{start_year + i // 12}-{i % 12 + 1:02d}" for i in range(n)]


def sdmx(series: dict, dims: dict, periods: list[str]) -> dict:
    """Minimal SDMX-JSON document in the shape the ABS API returns."""
    return {"data": {
        "structure": {"dimensions": {
            "series": [{"id": k, "values": [{"id": str(i), "name": n} for i, n in enumerate(v)]} for k, v in dims.items()],
            "observation": [{"id": "TIME_PERIOD", "values": [{"id": p} for p in periods]}],
        }},
        "dataSets": [{"series": {k: {"observations": {t: [v] for t, v in obs.items()}} for k, obs in series.items()}}],
    }}


def labour(start: str) -> dict:
    # Values are a pure function of the month, so re-fetching a window returns identical numbers.
    all_months = months(2024, 34 if STATE["advanced"] else 33)
    nsw_full = {p: 3.7 + 0.2 * ((i % 7) / 7) for i, p in enumerate(all_months)}
    aus_full = {p: 4.0 + 0.2 * ((i % 5) / 5) for i, p in enumerate(all_months)}
    nsw_full["2025-06"] = 31.0                       # in range but absurd   → flagged as an outlier, kept
    nsw_full["2025-09"] = 250.0                      # impossible percentage → dropped (range error)
    if STATE["advanced"]:
        nsw_full["2026-09"] = round(nsw_full["2026-09"] + 0.1, 3)   # ABS-style revision of last month's figure
    ps = [p for p in all_months if p >= start and p != "2025-03"]    # 2025-03: month the feed forgot to publish
    return sdmx({"0:0": {str(i): nsw_full[p] for i, p in enumerate(ps)}, "0:1": {str(i): aus_full[p] for i, p in enumerate(ps)}},
                {"MEASURE": ["Unemployment rate"], "REGION": ["New South Wales", "Australia"]}, ps)


def cpi(start: str) -> dict:
    qs = [q for q in (f"{y}-Q{q}" for y in range(2023, 2027) for q in range(1, 5)) if q >= start][:15]
    return sdmx({"0": {str(i): 130 + 0.9 * i for i in range(len(qs))}}, {"INDEX": ["All groups"]}, qs)


def building(start: str) -> dict:
    ps = [p for p in months(2024, 33) if p >= start]
    series = {"0:0:0": {str(i): 4300 + 30 * (i % 6) for i in range(len(ps))},       # NSW  ← wanted
              "1:0:0": {str(i): 3000 for i in range(len(ps))}}                        # VIC  ← must be filtered out
    return sdmx(series, {"REGION": ["New South Wales", "Victoria"], "MEASURE": ["Total dwelling units approved"],
                         "TSEST": ["Original"]}, ps)


def crime(offset: int, limit: int) -> dict:
    rows = [{"Year": y, "LGA": lga, "Offence": off, "Incidents": str(1000 + (y - 2019) * 12 + len(lga) * 7), "Rate": "900.5"}
            for y in range(2019, 2026) for lga in ("Sydney", "Parramatta", "Blacktown", "Bayside (NSW)")
            for off in ("Theft", "Assault (non-domestic)")]
    return {"success": True, "result": {"records": rows[offset:offset + limit]}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        start = q.get("startPeriod", ["0"])[0]
        if url.path == "/__advance":
            STATE["advanced"] = True
            body = {"advanced": True, "note": "next labour-force fetch includes a new month"}
        elif url.path.startswith("/data/LF/"):
            body = labour(start)
        elif url.path.startswith("/data/CPI/"):
            body = cpi(start)
        elif url.path.startswith("/data/BA_GCCSA"):
            body = building(start)
        elif url.path.endswith("datastore_search"):
            body = crime(int(q.get("offset", ["0"])[0]), int(q.get("limit", ["1000"])[0]))
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9000)
    args = ap.parse_args()
    print(f"Demo upstream on http://127.0.0.1:{args.port}  (generated data — not real statistics)")
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
