/** Shared tooltip for Recharts. `format(value, entry)` customises each value. */
export default function ChartTooltip({ active, payload, label, format = (v) => v }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#162844", border: "1px solid var(--border-accent)", borderRadius: 8, padding: "10px 14px", fontSize: 13, boxShadow: "0 8px 24px rgba(0,0,0,0.5)" }}>
      <p style={{ color: "var(--teal)", fontFamily: "var(--font-mono)", marginBottom: 6, fontSize: 11 }}>{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-primary)", marginBottom: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: p.type === "bar" ? 2 : "50%", background: p.color || p.fill, display: "inline-block", flexShrink: 0 }} />
          <span style={{ color: "var(--text-secondary)" }}>{p.name}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, marginLeft: "auto", paddingLeft: 12 }}>
            {p.value === null || p.value === undefined ? "—" : format(p.value, p)}
          </span>
        </div>
      ))}
    </div>
  );
}
