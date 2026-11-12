import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton, RangePicker } from "./ChartCard";
import ChartTooltip from "./ChartTooltip";

const RANGES = [
  { label: "12M", value: 12 }, { label: "2Y", value: 24 }, { label: "5Y", value: 60 }, { label: "All", value: 0 },
];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const formatPeriod = (p) => { if (!p) return ""; const [y, m] = p.split("-"); return `${MONTHS[parseInt(m, 10) - 1]} ${y.slice(2)}`; };
const axis = { fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" };

export default function UnemploymentChart() {
  const [months, setMonths] = useState(24);
  const { data, loading, error } = usePolling(() => api.getUnemploymentCompare(months), 60_000, [months]);
  const series = (data?.series ?? []).map((d) => ({ ...d, label: formatPeriod(d.period) }));

  return (
    <ChartCard
      title="Unemployment Rate"
      subtitle="NSW vs Australia — seasonally adjusted, monthly (ABS Labour Force)"
      delay={0.1} loading={loading && !data} error={error && !data ? error : null} empty={!loading && !series.length}
      controls={<>
        <RangePicker options={RANGES} value={months} onChange={setMonths} />
        <ExportButton filename="nsw-unemployment" rows={data?.series}
          columns={[{ key: "period", label: "Period" }, { key: "NSW", label: "NSW unemployment rate (%)" }, { key: "AUS", label: "Australia unemployment rate (%)" }]} />
      </>}
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={series} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval="preserveStartEnd" minTickGap={24} />
          <YAxis tick={axis} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} domain={["auto", "auto"]} />
          <Tooltip content={<ChartTooltip format={(v) => `${v.toFixed(2)}%`} />} />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
          <ReferenceLine y={4} stroke="var(--amber)" strokeDasharray="4 3" strokeWidth={1}
            label={{ value: "Full employment ~4%", fill: "var(--amber)", fontSize: 10, fontFamily: "var(--font-mono)" }} />
          <Line type="monotone" dataKey="NSW" name="NSW" stroke="var(--teal)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: "var(--teal)", strokeWidth: 0 }} />
          <Line type="monotone" dataKey="AUS" name="Australia" stroke="var(--amber)" strokeWidth={2} strokeDasharray="5 3" dot={false} activeDot={{ r: 5, fill: "var(--amber)", strokeWidth: 0 }} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
