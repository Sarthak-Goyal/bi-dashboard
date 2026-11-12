import { useEffect } from "react";
import { BarChart2, TrendingUp, ShieldAlert, Activity, Database, Home } from "lucide-react";

export const NAV = [
  { id: "overview", label: "Overview",       icon: BarChart2 },
  { id: "labour",   label: "Labour Force",   icon: TrendingUp },
  { id: "cpi",      label: "Cost of Living", icon: Activity },
  { id: "housing",  label: "Housing",        icon: Home },
  { id: "crime",    label: "NSW Crime",      icon: ShieldAlert },
  { id: "pipeline", label: "Pipeline Log",   icon: Database },
];

const SOURCES = [
  { name: "ABS Labour Force", freq: "Monthly" },
  { name: "ABS CPI", freq: "Quarterly" },
  { name: "ABS Approvals", freq: "Monthly" },
  { name: "NSW Open Data", freq: "Annual" },
];

/**
 * Sidebar — a fixed column on wide screens, an off-canvas drawer below 960px
 * (opened from the topbar menu button, closed by Esc, the scrim, or choosing a page).
 */
export default function Sidebar({ active, onChange, open, onClose }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose} aria-hidden="true" />
      <nav id="primary-nav" className={`sidebar ${open ? "open" : ""}`} aria-label="Dashboard sections">
        <div style={{ padding: "0 12px 16px" }}>
          <p style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", fontFamily: "var(--font-display)", padding: "4px 8px" }}>
            Data Views
          </p>
          {NAV.map(({ id, label, icon: Icon }) => {
            const isActive = active === id;
            return (
              <button key={id} type="button" className={`nav-btn ${isActive ? "active" : ""}`}
                aria-current={isActive ? "page" : undefined} onClick={() => onChange(id)}>
                <Icon size={15} strokeWidth={isActive ? 2.5 : 2} aria-hidden="true" />
                {label}
              </button>
            );
          })}
        </div>

        <div style={{ margin: "0 12px", padding: 12, background: "var(--bg-primary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.06em", fontFamily: "var(--font-display)", textTransform: "uppercase", marginBottom: 8 }}>
            Data Sources
          </p>
          {SOURCES.map((s) => (
            <div key={s.name} style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.name}</span>
              <span style={{ fontSize: 10, color: "var(--teal)", fontFamily: "var(--font-mono)", background: "var(--teal-dim)", padding: "1px 5px", borderRadius: 3, whiteSpace: "nowrap" }}>
                {s.freq}
              </span>
            </div>
          ))}
        </div>
      </nav>
    </>
  );
}
