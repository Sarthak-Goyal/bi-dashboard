import { useState } from "react";
import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton, RangePicker } from "./ChartCard";
import ChartTooltip from "./ChartTooltip";

const RANGES = [
  { label: "1Y", value: 4 }, { label: "3Y", value: 12 }, { label: "5Y", value: 20 }, { label: "All", value: 0 },
];
const axis = { fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" };

export default function CPIChart() {
  const [quarters, setQuarters] = useState(20);
  const { data, loading, error } = usePolling(() => api.getCPI(quarters), 120_000, [quarters]);
  const series = data?.series ?? [];

  return (
    <ChartCard
      title="Consumer Price Index — Sydney"
      subtitle="All groups index + annual % change (ABS CPI, quarterly)"
      delay={0.2} loading={loading && !data} error={error && !data ? error : null} empty={!loading && !series.length}
      controls={<>
        <RangePicker options={RANGES} value={quarters} onChange={setQuarters} />
        <ExportButton filename="sydney-cpi" rows={series}
          columns={[{ key: "period", label: "Quarter" }, { key: "index_value", label: "CPI index" }, { key: "pct_change_annual", label: "Annual change (%)" }]} />
      </>}
    >
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={series} margin={{ top: 4, right: 30, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="period" tick={{ ...axis, fontSize: 10 }} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval="preserveStartEnd" minTickGap={24} />
          <YAxis yAxisId="index" orientation="left" tick={axis} tickLine={false} axisLine={false} domain={["auto", "auto"]} tickFormatter={(v) => v.toFixed(0)} />
          <YAxis yAxisId="pct" orientation="right" tick={{ ...axis, fill: "var(--amber)" }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v.toFixed(1)}%`} domain={[-1, "auto"]} />
          <Tooltip content={<ChartTooltip format={(v, p) => (p.dataKey === "pct_change_annual" ? `${v.toFixed(2)}%` : v.toFixed(1))} />} />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
          <ReferenceLine yAxisId="pct" y={3} stroke="var(--green)" strokeDasharray="3 3" strokeWidth={1}
            label={{ value: "RBA target band 2–3%", fill: "var(--green)", fontSize: 10, fontFamily: "var(--font-mono)", position: "insideTopLeft" }} />
 <ReferenceLine yAxisId="pct" y={2} stroke="var(--green)" strokeDasharray="3 3" strokeWidth={1} />
          <Bar yAxisId="pct" dataKey="pct_change_annual" name="Annual % Change" fill="var(--amber)" fillOpacity={0.4} radius={[2, 2, 0, 0]} />
          <Line yAxisId="index" type="monotone" dataKey="index_value" name="CPI Index" stroke="var(--teal)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: "var(--teal)", strokeWidth: 0 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
