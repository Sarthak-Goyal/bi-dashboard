import { useState } from "react";
import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton, RangePicker } from "./ChartCard";
import ChartTooltip from "./ChartTooltip";

const RANGES = [{ label: "12M", value: 12 }, { label: "3Y", value: 36 }, { label: "All", value: 0 }];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmt = (p) => { const [y, m] = p.split("-"); return `${MONTHS[parseInt(m, 10) - 1]} ${y.slice(2)}`; };
const axis = { fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" };

/** Multi-source join: building approvals ⨝ unemployment ⟕ CPI, joined on period. */
export default function HousingChart() {
  const [months, setMonths] = useState(36);
  const { data, loading, error } = usePolling(() => api.getHousingLabour(months), 120_000, [months]);
  const series = (data?.series ?? []).map((d) => ({ ...d, label: fmt(d.period) }));
  const stats = data?.stats;

  return (
    <ChartCard
      title="Housing Approvals vs Labour Market"
      subtitle="Three ABS sources joined by period: dwelling approvals, unemployment rate, CPI annual change"
      height={320} delay={0.1} loading={loading && !data} error={error && !data ? error : null}
      empty={!loading && !series.length} emptyMessage="Not enough overlapping data to join yet."
      controls={<>
        <RangePicker options={RANGES} value={months} onChange={setMonths} />
        <ExportButton filename="nsw-housing-labour-cpi" rows={data?.series}
          columns={[{ key: "period", label: "Period" }, { key: "approvals", label: "Dwelling approvals" },
            { key: "approvals_3m_avg", label: "Approvals 3-month avg" }, { key: "unemployment_rate", label: "Unemployment rate (%)" },
            { key: "cpi_annual", label: "CPI annual change (%)" }]} />
      </>}
      footer={stats?.correlation !== null && stats?.correlation !== undefined
        ? <>Correlation of approvals vs unemployment over {stats.n} months: <strong style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{stats.correlation}</strong>. {stats.note}</>
        : null}
    >
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={series} margin={{ top: 4, right: 12, left: -6, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval="preserveStartEnd" minTickGap={24} />
          <YAxis yAxisId="units" orientation="left" tick={axis} tickLine={false} axisLine={false} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v)} />
          <YAxis yAxisId="pct" orientation="right" tick={{ ...axis, fill: "var(--amber)" }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} domain={["auto", "auto"]} />
          <Tooltip content={<ChartTooltip format={(v, p) => (p.dataKey === "approvals" || p.dataKey === "approvals_3m_avg" ? Math.round(v).toLocaleString() : `${v.toFixed(2)}%`)} />} />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
          <Bar yAxisId="units" dataKey="approvals" name="Dwelling approvals" fill="var(--teal)" fillOpacity={0.35} radius={[2, 2, 0, 0]} />
          <Line yAxisId="units" type="monotone" dataKey="approvals_3m_avg" name="Approvals (3-mo avg)" stroke="var(--teal)" strokeWidth={2.5} dot={false} />
          <Line yAxisId="pct" type="monotone" dataKey="unemployment_rate" name="Unemployment rate" stroke="var(--amber)" strokeWidth={2} dot={false} />
          <Line yAxisId="pct" type="stepAfter" dataKey="cpi_annual" name="CPI annual change" stroke="var(--red)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
