import { BarChart2, TrendingUp, ShieldAlert, Activity, Database } from "lucide-react";

const NAV = [
  { id: "overview",    label: "Overview",       icon: BarChart2 },
  { id: "labour",      label: "Labour Force",   icon: TrendingUp },
  { id: "cpi",         label: "Cost of Living", icon: Activity },
  { id: "crime",       label: "NSW Crime",      icon: ShieldAlert },
  { id: "pipeline",    label: "Pipeline Log",   icon: Database },
];

export default function Sidebar({ active, onChange }) {
  return (
    <nav className="sidebar">
      <div style={{ padding: "0 12px 16px" }}>
        <p style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", fontFamily: "var(--font-display)", padding: "4px 8px" }}>
          Data Views
        </p>
        {NAV.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              style={{
                width: "100%", display: "flex", alignItems: "center", gap: 10,
                padding: "9px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                background: isActive ? "var(--teal-dim)" : "transparent",
                color: isActive ? "var(--teal)" : "var(--text-secondary)",
                fontSize: 13, fontFamily: "var(--font-body)", fontWeight: isActive ? 600 : 400,
                textAlign: "left", transition: "all 0.15s", marginBottom: 2,
                borderLeft: isActive ? "2px solid var(--teal)" : "2px solid transparent",
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
            >
              <Icon size={15} strokeWidth={isActive ? 2.5 : 2} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Data sources info */}
      <div style={{ margin: "0 12px", padding: "12px", background: "var(--bg-primary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <p style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.06em", fontFamily: "var(--font-display)", textTransform: "uppercase", marginBottom: 8 }}>
          Live Sources
        </p>
        {[
          { name: "ABS Labour Force", freq: "Monthly" },
          { name: "ABS CPI", freq: "Quarterly" },
          { name: "NSW Open Data", freq: "Annual" },
        ].map(s => (
          <div key={s.name} style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.name}</span>
            <span style={{ fontSize: 10, color: "var(--teal)", fontFamily: "var(--font-mono)", background: "var(--teal-dim)", padding: "1px 5px", borderRadius: 3 }}>
              {s.freq}
            </span>
          </div>
        ))}
      </div>
    </nav>
  );
}
