import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#162844", border: "1px solid var(--border-accent)", borderRadius: 8,
      padding: "10px 14px", fontSize: 13,
    }}>
      <p style={{ color: "var(--teal)", fontFamily: "var(--font-mono)", marginBottom: 6, fontSize: 11 }}>{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-primary)" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.color, display: "inline-block" }} />
          <span style={{ color: "var(--text-secondary)" }}>{p.name}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{p.value?.toFixed(2)}%</span>
        </div>
      ))}
    </div>
  );
};

export default function UnemploymentChart() {
  const { data, loading, error } = usePolling(() => api.getUnemploymentCompare(), 60_000);

  const series = data?.series ?? [];
  // Format period "2023-03" → "Mar 23"
  const formatted = series.map(d => ({
    ...d,
    label: formatPeriod(d.period),
  }));

  return (
    <div className="card" style={{ animation: "fadeIn 0.4s ease 0.1s both" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 15, color: "var(--text-primary)" }}>
            Unemployment Rate
          </h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
            NSW vs Australia — seasonally adjusted, monthly (ABS Labour Force)
          </p>
        </div>
        <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)", background: "var(--bg-secondary)", padding: "3px 8px", borderRadius: 4 }}>
          Last 24 months
        </span>
      </div>

      {loading ? (
        <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 13 }}>
          Loading data…
        </div>
      ) : error ? (
        <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--red)", fontSize: 13 }}>
          Error: {error}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={formatted} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `${v}%`}
              domain={["auto", "auto"]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
              formatter={(val) => <span style={{ color: "var(--text-secondary)", fontFamily: "var(--font-body)" }}>{val}</span>}
            />
            {/* Full employment reference line */}
            <ReferenceLine y={4} stroke="var(--amber)" strokeDasharray="4 3" strokeWidth={1}
              label={{ value: "Full employment ~4%", fill: "var(--amber)", fontSize: 10, fontFamily: "var(--font-mono)" }} />
            <Line
              type="monotone" dataKey="NSW" name="NSW"
              stroke="var(--teal)" strokeWidth={2.5}
              dot={false} activeDot={{ r: 5, fill: "var(--teal)", strokeWidth: 0 }}
            />
            <Line
              type="monotone" dataKey="AUS" name="Australia"
              stroke="var(--amber)" strokeWidth={2} strokeDasharray="5 3"
              dot={false} activeDot={{ r: 5, fill: "var(--amber)", strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function formatPeriod(period) {
  if (!period) return "";
  const [yr, mo] = period.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(mo) - 1]} ${yr.slice(2)}`;
}
