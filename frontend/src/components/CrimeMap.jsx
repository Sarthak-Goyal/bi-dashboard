import { useEffect, useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { useOnce } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton } from "./ChartCard";

const W = 640, H = 520;
// Sequential teal ramp, low → high (5 classes, quantile breaks)
const RAMP = ["#14405a", "#106a7d", "#0a9a99", "#12c9b8", "#7ff5e4"];
const NO_DATA = "#1b2b44";

// Greater Sydney bounding box (wound clockwise, as d3-geo expects)
const SYDNEY_BOX = {
  type: "Feature",
  geometry: { type: "Polygon", coordinates: [[[150.55, -34.25], [150.55, -33.5], [151.4, -33.5], [151.4, -34.25], [150.55, -34.25]]] },
};

const norm = (s) => String(s).toLowerCase().replace(/\(nsw\)/g, "").replace(/[^a-z0-9]/g, "");
const METRICS = [
  { id: "rate", label: "Rate per 100k", get: (r) => r?.rate_per_100k, fmt: (v) => Math.round(v).toLocaleString() },
  { id: "incidents", label: "Incidents", get: (r) => r?.incidents, fmt: (v) => v.toLocaleString() },
];

function quantileBreaks(values, classes = RAMP.length) {
  const v = [...values].sort((a, b) => a - b);
  if (!v.length) return [];
  return Array.from({ length: classes - 1 }, (_, i) => v[Math.min(v.length - 1, Math.floor(((i + 1) / classes) * v.length))]);
}
const classOf = (value, breaks) => breaks.filter((b) => value >= b).length;

export default function CrimeMap() {
  const [geo, setGeo] = useState(null);
  const [geoError, setGeoError] = useState(null);
  const [offence, setOffence] = useState("All");
  const [metricId, setMetricId] = useState("rate");
  const [view, setView] = useState("nsw");
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);

  const offences = useOnce(() => api.getCrimeOffences());
  const { data, loading, error } = useOnce(() => api.getCrimeByLGA(offence), [offence]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}geo/nsw_lga.geojson`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((g) => !cancelled && setGeo(g))
      .catch((e) => !cancelled && setGeoError(e.message));
    return () => { cancelled = true; };
  }, []);

  const metric = METRICS.find((m) => m.id === metricId);
  const rows = data?.series ?? [];
  const byName = useMemo(() => new Map(rows.map((r) => [norm(r.lga), r])), [rows]);

  const path = useMemo(() => {
    if (!geo) return null;
    const projection = geoMercator().fitExtent([[6, 6], [W - 6, H - 6]], view === "sydney" ? SYDNEY_BOX : geo);
    return geoPath(projection);
  }, [geo, view]);

  const features = useMemo(() => {
    if (!geo || !path) return [];
    return geo.features.map((f) => {
      const row = byName.get(norm(f.properties.name));
      const value = metric.get(row);
      return { name: f.properties.name, d: path(f), row, value: value ?? null };
    });
  }, [geo, path, byName, metric]);

  const values = features.filter((f) => f.value !== null).map((f) => f.value);
  const breaks = useMemo(() => quantileBreaks(values), [values.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps
  const colourFor = (v) => (v === null ? NO_DATA : RAMP[classOf(v, breaks)]);

  const ranked = useMemo(
    () => features.filter((f) => f.value !== null).sort((a, b) => b.value - a.value).slice(0, 10),
    [features],
  );
  const matched = features.filter((f) => f.row).length;
  const active = features.find((f) => f.name === (hover ?? selected));

  const exportRows = rows.map((r) => ({ lga: r.lga, incidents: r.incidents, rate_per_100k: r.rate_per_100k }));
  const offenceOptions = ["All", ...(offences.data?.offences ?? [])];

  return (
    <ChartCard
      title="Crime by Local Government Area"
      subtitle={`Choropleth of ${data?.year ?? "latest year"} — ${metric.label.toLowerCase()}, ${offence === "All" ? "all offences" : offence.toLowerCase()}`}
      height={420} delay={0.2}
      loading={(loading && !data) || (!geo && !geoError)} error={geoError ? `Boundary file: ${geoError}` : error && !data ? error : null}
      empty={!loading && !rows.length} emptyMessage="No crime data yet."
      controls={<>
        <label className="sr-only" htmlFor="map-offence">Offence</label>
        <select id="map-offence" className="select" value={offence} onChange={(e) => { setOffence(e.target.value); setSelected(null); }}>
          {offenceOptions.map((o) => <option key={o} value={o}>{o === "All" ? "All offences" : o}</option>)}
        </select>
        <div role="group" aria-label="Map measure" className="range-picker">
          {METRICS.map((m) => (
            <button key={m.id} type="button" aria-pressed={metricId === m.id} className={metricId === m.id ? "active" : ""} onClick={() => setMetricId(m.id)}>{m.label}</button>
          ))}
        </div>
        <div role="group" aria-label="Map extent" className="range-picker">
          {[["nsw", "NSW"], ["sydney", "Sydney"]].map(([id, label]) => (
            <button key={id} type="button" aria-pressed={view === id} className={view === id ? "active" : ""} onClick={() => setView(id)}>{label}</button>
          ))}
        </div>
        <ExportButton filename={`nsw-crime-by-lga-${offence === "All" ? "all" : offence.toLowerCase().replace(/\W+/g, "-")}`} rows={exportRows}
          columns={[{ key: "lga", label: "LGA" }, { key: "incidents", label: "Incidents" }, { key: "rate_per_100k", label: "Rate per 100k" }]} />
      </>}
      footer={<>
        {matched} of {features.length} council areas have data. Boundaries: ABS ASGS Edition 3 (CC BY 4.0, © Commonwealth of Australia), simplified for display.
      </>}
    >
      <div className="map-layout">
        <div style={{ position: "relative", minWidth: 0 }}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" style={{ width: "100%", height: "auto", maxHeight: 520, display: "block", overflow: "hidden", borderRadius: 8, background: "var(--bg-secondary)" }}
            aria-label={`Map of NSW local government areas shaded by ${metric.label.toLowerCase()}. Top areas are listed beside the map.`}>
            {features.map((f) => (
              <path key={f.name} d={f.d} fill={colourFor(f.value)} stroke={f.name === selected ? "#fff" : "rgba(8,15,30,0.9)"}
                strokeWidth={f.name === selected ? 1.6 : view === "sydney" ? 0.8 : 0.4}
                style={{ cursor: f.row ? "pointer" : "default", transition: "fill 0.2s" }}
                onMouseEnter={() => setHover(f.name)} onMouseLeave={() => setHover(null)}
                onClick={() => f.row && setSelected(f.name === selected ? null : f.name)}>
                <title>{f.row ? `${f.name}: ${metric.fmt(f.value)} ${metric.id === "rate" ? "per 100k" : "incidents"}` : `${f.name}: no data`}</title>
              </path>
            ))}
          </svg>
          {/* Legend */}
          <div style={{ position: "absolute", left: 10, bottom: 10, background: "rgba(8,15,30,0.82)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px", fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
            <div style={{ marginBottom: 4 }}>{metric.label}</div>
            <div style={{ display: "flex" }}>
              {RAMP.map((c) => <span key={c} style={{ width: 22, height: 8, background: c }} />)}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 3 }}>
              <span>{values.length ? metric.fmt(Math.min(...values)) : ""}</span>
              <span>{values.length ? metric.fmt(Math.max(...values)) : ""}</span>
            </div>
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <div aria-live="polite" style={{ minHeight: 64, background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px", marginBottom: 12 }}>
            {active?.row ? (
              <>
                <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 14 }}>{active.name}</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                  {active.row.incidents.toLocaleString()} incidents
                  {active.row.rate_per_100k != null && <> · {Math.round(active.row.rate_per_100k).toLocaleString()} per 100k</>}
                </div>
              </>
            ) : (
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Hover or select a council area, or pick one from the ranking.</span>
            )}
          </div>
          <h4 style={{ fontFamily: "var(--font-display)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: 6 }}>
            Top 10 · {metric.label}
          </h4>
          <ol style={{ listStyle: "none" }}>
            {ranked.map((f, i) => (
              <li key={f.name}>
                <button type="button" className="rank-row" aria-pressed={selected === f.name}
                  onClick={() => setSelected(f.name === selected ? null : f.name)}
                  onMouseEnter={() => setHover(f.name)} onMouseLeave={() => setHover(null)}>
                  <span style={{ width: 18, color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}>{i + 1}</span>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: colourFor(f.value), flexShrink: 0 }} />
                  <span style={{ flex: 1, textAlign: "left", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{metric.fmt(f.value)}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </ChartCard>
  );
}
