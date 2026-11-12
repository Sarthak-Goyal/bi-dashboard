import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LineChart, Line, Legend,
} from "recharts";
import { useOnce } from "../hooks/useMetrics";
import { api } from "../utils/api";

const OFFENCE_COLOURS = [
  "var(--teal)", "var(--amber)", "#a78bfa", "#f87171",
  "#34d399", "#60a5fa", "#fb923c", "#e879f9",
];

export function CrimeByOffenceChart() {
  const { data, loading, error } = useOnce(() => api.getCrimeByOffence());
  const series = data?.series ?? [];

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: "#162844", border: "1px solid var(--border-accent)", borderRadius: 8, padding: "10px 14px" }}>
        <p style={{ color: "var(--teal)", fontFamily: "var(--font-mono)", fontSize: 11, marginBottom: 4 }}>{label}</p>
        <p style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
          {payload[0]?.value?.toLocaleString()} incidents
        </p>
      </div>
    );
  };

  return (
    <div className="card" style={{ animation: "fadeIn 0.4s ease 0.3s both" }}>
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 15 }}>
          Recorded Crime by Offence
        </h3>
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
          Total incidents across all NSW LGAs — {data?.year ?? "latest year"} (NSW Open Data)
        </p>
      </div>

      {loading ? (
        <div style={{ height: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 13 }}>Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={series} layout="vertical" margin={{ top: 0, right: 20, left: 80, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false} axisLine={false}
              tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}
            />
            <YAxis
              type="category" dataKey="offence"
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              tickLine={false} axisLine={false} width={80}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
            <Bar dataKey="total" radius={[0, 4, 4, 0]}>
              {series.map((_, i) => (
                <Cell key={i} fill={OFFENCE_COLOURS[i % OFFENCE_COLOURS.length]} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export function CrimeTrendChart() {
  const OFFENCES = ["Theft", "Assault (non-domestic)", "Drug offences", "Property damage", "Break and enter"];
  const [selectedOffence, setSelectedOffence] = useState("Theft");
  const { data, loading, refetch } = useOnce(() => api.getCrimeTrend(selectedOffence), [selectedOffence]);

  const series = data?.series ?? [];
  const lgas = data?.lgas ?? [];

  const COLOURS = ["var(--teal)", "var(--amber)", "#a78bfa", "#f87171", "#34d399"];

  function handleOffenceChange(o) {
    setSelectedOffence(o);
    // useOnce won't auto-refetch so we manually re-call
    refetch();
  }

  return (
    <div className="card" style={{ animation: "fadeIn 0.4s ease 0.4s both" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 15 }}>Crime Trend — Top LGAs</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>Year-on-year for top 5 LGAs by volume</p>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {OFFENCES.map(o => (
            <button key={o} onClick={() => setSelectedOffence(o)} style={{
              background: selectedOffence === o ? "var(--teal-dim)" : "var(--bg-secondary)",
              border: `1px solid ${selectedOffence === o ? "var(--border-accent)" : "var(--border)"}`,
              color: selectedOffence === o ? "var(--teal)" : "var(--text-secondary)",
              borderRadius: 5, padding: "3px 10px", fontSize: 11, cursor: "pointer",
              fontFamily: "var(--font-body)", transition: "all 0.15s",
            }}>
              {o}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ height: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 13 }}>Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={series} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="year"
              tick={{ fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false} axisLine={{ stroke: "var(--border)" }}
            />
            <YAxis
              tick={{ fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false} axisLine={false}
              tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v}
            />
            <Tooltip
              contentStyle={{ background: "#162844", border: "1px solid var(--border-accent)", borderRadius: 8, fontSize: 13 }}
              labelStyle={{ color: "var(--teal)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {lgas.map((lga, i) => (
              <Line key={lga} type="monotone" dataKey={lga}
                stroke={COLOURS[i % COLOURS.length]} strokeWidth={2}
                dot={{ r: 3, fill: COLOURS[i % COLOURS.length], strokeWidth: 0 }}
                activeDot={{ r: 5, strokeWidth: 0 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
