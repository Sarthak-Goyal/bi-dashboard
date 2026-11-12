import { Download, BarChart3 } from "lucide-react";
import { downloadCsv, stamp } from "../utils/csv";

/** Shimmering placeholder shaped like a chart (replaces "Loading…" text). */
export function ChartSkeleton({ height = 260 }) {
  const bars = [38, 56, 44, 70, 52, 82, 60, 90, 66, 74, 48, 58];
  return (
    <div role="status" aria-label="Loading chart" style={{ height, position: "relative", display: "flex", alignItems: "flex-end", gap: 8, padding: "8px 8px 22px" }}>
      {[0.25, 0.5, 0.75].map((t) => (
        <div key={t} style={{ position: "absolute", left: 8, right: 8, bottom: 22 + (height - 40) * t, borderTop: "1px dashed rgba(255,255,255,0.06)" }} />
      ))}
      {bars.map((h, i) => (
        <div key={i} className="skeleton" style={{ flex: 1, height: `${h}%`, borderRadius: "4px 4px 0 0", animationDelay: `${i * 0.08}s` }} />
      ))}
      <span className="sr-only">Loading data…</span>
    </div>
  );
}

export function ChartEmpty({ height = 260, message = "No data available yet." }) {
  return (
    <div style={{ height, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 16 }}>
      <BarChart3 size={22} strokeWidth={1.5} />
      <span>{message}</span>
    </div>
  );
}

export function ChartError({ height = 260, message }) {
  return (
    <div role="alert" style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--red)", fontSize: 13, textAlign: "center", padding: 16 }}>
      Couldn’t load this chart. {message}
    </div>
  );
}

/** Segmented date-range control, e.g. 12M · 2Y · 5Y · All. */
export function RangePicker({ options, value, onChange, label = "Date range" }) {
  return (
    <div role="group" aria-label={label} className="range-picker">
      {options.map((o) => (
        <button key={o.label} type="button" aria-pressed={value === o.value}
          className={value === o.value ? "active" : ""} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** "Download CSV" button — builds the file in the browser from the chart's data. */
export function ExportButton({ filename, rows, columns, disabled }) {
  const empty = !rows?.length;
  return (
    <button type="button" className="icon-btn" disabled={disabled || empty}
      title={empty ? "Nothing to export yet" : "Download this data as CSV"}
      onClick={() => downloadCsv(`${filename}-${stamp()}.csv`, rows, columns)}>
      <Download size={12} aria-hidden="true" />
      <span>CSV</span>
    </button>
  );
}

/**
 * ChartCard — shared frame for every chart: title, subtitle, controls,
 * and consistent loading / error / empty states.
 */
export default function ChartCard({
  title, subtitle, controls, loading, error, empty, emptyMessage, height = 260, delay = 0, children, footer,
}) {
  return (
    <section className="card" style={{ animation: `fadeIn 0.4s ease ${delay}s both`, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 15 }}>{title}</h3>
          {subtitle && <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{subtitle}</p>}
        </div>
        {controls && <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>{controls}</div>}
      </div>
      {loading ? <ChartSkeleton height={height} />
        : error ? <ChartError height={height} message={error} />
        : empty ? <ChartEmpty height={height} message={emptyMessage} />
        : children}
      {footer && !loading && <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>{footer}</div>}
    </section>
  );
}
