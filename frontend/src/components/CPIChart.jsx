import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#162844", border: "1px solid var(--border-accent)", borderRadius: 8, padding: "10px 14px", fontSize: 13 }}>
      <p style={{ color: "var(--teal)", fontFamily: "var(--font-mono)", marginBottom: 6, fontSize: 11 }}>{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-primary)", marginBottom: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: p.type === "bar" ? 2 : "50%", background: p.fill || p.color, display: "inline-block" }} />
          <span style={{ color: "var(--text-secondary)" }}>{p.name}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
            {p.dataKey === "pct_change_annual" ? `${p.value?.toFixed(2)}%` : p.value?.toFixed(1)}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function CPIChart() {
  const { data, loading, error } = usePolling(() => api.getCPI(20), 120_000);
  const series = (data?.series ?? []).map(d => ({
    ...d,
    label: d.period,
  }));

  return (
    <div className="card" style={{ animation: "fadeIn 0.4s ease 0.2s both" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 15 }}>
            Consumer Price Index — Sydney
          </h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
            All groups index + annual % change (ABS CPI, quarterly)
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 13 }}>Loading data…</div>
      ) : error ? (
        <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--red)", fontSize: 13 }}>Error: {error}</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={series} margin={{ top: 4, right: 30, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              interval="preserveStartEnd"
            />
            {/* Left Y axis — index value */}
            <YAxis
              yAxisId="index"
              orientation="left"
              tick={{ fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false} axisLine={false}
              domain={["auto", "auto"]}
              tickFormatter={v => v.toFixed(0)}
            />
            {/* Right Y axis — annual % change */}
            <YAxis
              yAxisId="pct"
              orientation="right"
              tick={{ fill: "var(--amber)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false} axisLine={false}
              tickFormatter={v => `${v.toFixed(1)}%`}
              domain={[-1, "auto"]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
            {/* RBA target band: 2-3% */}
            <ReferenceLine yAxisId="pct" y={3} stroke="var(--green)" strokeDasharray="3 3" strokeWidth={1}
              label={{ value: "RBA target 3%", fill: "var(--green)", fontSize: 10, fontFamily: "var(--font-mono)", position: "right" }} />
            <ReferenceLine yAxisId="pct" y={2} stroke="var(--green)" strokeDasharray="3 3" strokeWidth={1}
              label={{ value: "2%", fill: "var(--green)", fontSize: 10, fontFamily: "var(--font-mono)", position: "right" }} />
            {/* Annual % change as bars */}
            <Bar yAxisId="pct" dataKey="pct_change_annual" name="Annual % Change"
              fill="var(--amber)" fillOpacity={0.4} radius={[2, 2, 0, 0]} />
            {/* Index value as line */}
            <Line yAxisId="index" type="monotone" dataKey="index_value" name="CPI Index"
              stroke="var(--teal)" strokeWidth={2.5} dot={false}
              activeDot={{ r: 5, fill: "var(--teal)", strokeWidth: 0 }} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
