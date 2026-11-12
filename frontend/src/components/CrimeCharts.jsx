import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line, Legend } from "recharts";
import { useOnce } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton, RangePicker } from "./ChartCard";
import ChartTooltip from "./ChartTooltip";

const OFFENCE_COLOURS = ["var(--teal)", "var(--amber)", "#a78bfa", "#f87171", "#34d399", "#60a5fa", "#fb923c", "#e879f9"];
const axis = { fill: "var(--text-secondary)", fontSize: 11, fontFamily: "var(--font-mono)" };

export function CrimeByOffenceChart() {
  const { data, loading, error } = useOnce(() => api.getCrimeByOffence());
  const series = data?.series ?? [];
  return (
    <ChartCard
      title="Recorded Crime by Offence"
      subtitle={`Total incidents across all NSW LGAs — ${data?.year ?? "latest year"} (NSW Open Data)`}
      height={240} delay={0.3} loading={loading} error={error} empty={!loading && !series.length}
      controls={<ExportButton filename="nsw-crime-by-offence" rows={series}
        columns={[{ key: "offence", label: "Offence" }, { key: "total", label: `Incidents (${data?.year ?? ""})` }]} />}
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={series} layout="vertical" margin={{ top: 0, right: 20, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
          <XAxis type="number" tick={{ ...axis, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)} />
          <YAxis type="category" dataKey="offence" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} tickLine={false} axisLine={false} width={118} />
          <Tooltip content={<ChartTooltip format={(v) => `${v.toLocaleString()} incidents`} />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="total" name="Incidents" radius={[0, 4, 4, 0]}>
            {series.map((_, i) => <Cell key={i} fill={OFFENCE_COLOURS[i % OFFENCE_COLOURS.length]} fillOpacity={0.85} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

const TREND_RANGES = [{ label: "3Y", value: 3 }, { label: "5Y", value: 5 }, { label: "All", value: 0 }];

export function CrimeTrendChart() {
  const [offence, setOffence] = useState("Theft");
  const [years, setYears] = useState(0);
  const offences = useOnce(() => api.getCrimeOffences());
  const { data, loading, error } = useOnce(() => api.getCrimeTrend(offence, years), [offence, years]);
  const series = data?.series ?? [];
  const lgas = data?.lgas ?? [];
  const options = (offences.data?.offences?.length ? offences.data.offences : ["Theft"]).slice(0, 6);

  return (
    <ChartCard
      title="Crime Trend — Top LGAs"
      subtitle="Year-on-year for the top 5 LGAs by volume"
      height={240} delay={0.4} loading={loading && !data} error={error && !data ? error : null} empty={!loading && !series.length}
      controls={<>
        <label className="sr-only" htmlFor="trend-offence">Offence</label>
        <select id="trend-offence" className="select" value={offence} onChange={(e) => setOffence(e.target.value)}>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <RangePicker options={TREND_RANGES} value={years} onChange={setYears} />
        <ExportButton filename={`nsw-crime-trend-${offence.toLowerCase().replace(/\W+/g, "-")}`} rows={series}
          columns={[{ key: "year", label: "Year" }, ...lgas.map((l) => ({ key: l, label: `${l} incidents` }))]} />
      </>}
    >
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={series} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="year" tick={axis} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
          <YAxis tick={axis} tickLine={false} axisLine={false} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v)} />
          <Tooltip content={<ChartTooltip format={(v) => v.toLocaleString()} />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {lgas.map((lga, i) => (
            <Line key={lga} type="monotone" dataKey={lga} stroke={OFFENCE_COLOURS[i % OFFENCE_COLOURS.length]} strokeWidth={2}
              dot={{ r: 3, fill: OFFENCE_COLOURS[i % OFFENCE_COLOURS.length], strokeWidth: 0 }} activeDot={{ r: 5, strokeWidth: 0 }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
