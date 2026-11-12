import { useState } from "react";
import { MapPin, RefreshCw, Github } from "lucide-react";
import { usePolling } from "./hooks/useMetrics";
import { api } from "./utils/api";
import Sidebar from "./components/Sidebar";
import PipelineStatus from "./components/PipelineStatus";
import KPICard from "./components/KPICard";
import UnemploymentChart from "./components/UnemploymentChart";
import CPIChart from "./components/CPIChart";
import { CrimeByOffenceChart, CrimeTrendChart } from "./components/CrimeCharts";
import PipelineLog from "./components/PipelineLog";

// ── Overview page ──────────────────────────────────────────────────────────
function Overview() {
  const { data, loading } = usePolling(() => api.getSummary(), 30_000);
  const s = data ?? {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
          NSW Economic Dashboard
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
          Live data pipeline · ABS Labour Force, CPI &amp; NSW Open Data
        </p>
      </div>

      {/* KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <KPICard
          label="Unemployment Rate"
          value={s.unemployment_rate?.value}
          unit="%"
          delta={s.unemployment_rate?.delta}
          deltaUnit=" pts"
          description={s.unemployment_rate?.description}
          period={s.unemployment_rate?.period}
          accent="var(--teal)"
          invertGood={true}
          loading={loading}
        />
        <KPICard
          label="Participation Rate"
          value={s.participation_rate?.value}
          unit="%"
          delta={s.participation_rate?.delta}
          deltaUnit=" pts"
          description={s.participation_rate?.description}
          period={s.participation_rate?.period}
          accent="var(--green)"
          loading={loading}
        />
        <KPICard
          label="CPI Annual Change"
          value={s.cpi_annual_change?.value}
          unit="%"
          description={s.cpi_annual_change?.description}
          period={s.cpi_annual_change?.period}
          accent="var(--amber)"
          invertGood={true}
          loading={loading}
        />
        <KPICard
          label="Recorded Crime"
          value={s.crime_incidents?.value}
          unit=""
          delta={s.crime_incidents?.delta_pct}
          deltaUnit="%"
          description={s.crime_incidents?.description}
          period={String(s.crime_incidents?.year ?? "")}
          accent="var(--red)"
          invertGood={true}
          loading={loading}
        />
      </div>

      {/* Charts row 1 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <UnemploymentChart />
        <CPIChart />
      </div>

      {/* Charts row 2 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <CrimeByOffenceChart />
        <CrimeTrendChart />
      </div>
    </div>
  );
}

// ── Labour Force page ──────────────────────────────────────────────────────
function LabourPage() {
  const { data, loading } = usePolling(() => api.getSummary(), 30_000);
  const s = data ?? {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Labour Force</h2>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>ABS Labour Force Survey — seasonally adjusted monthly data</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <KPICard label="Unemployment Rate" value={s.unemployment_rate?.value} unit="%" delta={s.unemployment_rate?.delta} deltaUnit=" pts"
          description="NSW, seasonally adjusted" period={s.unemployment_rate?.period} accent="var(--teal)" invertGood loading={loading} />
        <KPICard label="Participation Rate" value={s.participation_rate?.value} unit="%" delta={s.participation_rate?.delta} deltaUnit=" pts"
          description="NSW, seasonally adjusted" period={s.participation_rate?.period} accent="var(--green)" loading={loading} />
      </div>
      <UnemploymentChart />
      <div className="card" style={{ padding: 20 }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 14, marginBottom: 8 }}>About this data</h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
          Sourced from the <strong style={{ color: "var(--teal)" }}>ABS Labour Force Survey</strong> via the ABS SDMX Data API
          (<code style={{ fontFamily: "var(--font-mono)", fontSize: 11, background: "var(--bg-secondary)", padding: "1px 5px", borderRadius: 3 }}>api.data.abs.gov.au</code>).
          Dataflow <code style={{ fontFamily: "var(--font-mono)", fontSize: 11, background: "var(--bg-secondary)", padding: "1px 5px", borderRadius: 3 }}>LF</code> —
          measures M6 (unemployment rate) and M7 (participation rate), adjustment type 20 (seasonally adjusted),
          region 1 (NSW) and 9 (Australia), persons, all ages, monthly frequency.
          The pipeline refreshes hourly and stores results in SQLite.
        </p>
      </div>
    </div>
  );
}

// ── CPI page ───────────────────────────────────────────────────────────────
function CPIPage() {
  const { data, loading } = usePolling(() => api.getSummary(), 30_000);
  const s = data ?? {};
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Cost of Living</h2>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>ABS Consumer Price Index — Sydney, all groups, quarterly</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <KPICard label="CPI Annual Change" value={s.cpi_annual_change?.value} unit="%" description="All groups, Sydney"
          period={s.cpi_annual_change?.period} accent="var(--amber)" invertGood loading={loading} />
        <KPICard label="CPI Index" value={s.cpi_annual_change?.index_value} unit=""
          description="All groups index value" period={s.cpi_annual_change?.period} accent="var(--teal)" loading={loading} />
      </div>
      <CPIChart />
    </div>
  );
}

// ── Crime page ─────────────────────────────────────────────────────────────
function CrimePage() {
  const { data, loading } = usePolling(() => api.getSummary(), 30_000);
  const s = data ?? {};
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>NSW Crime Statistics</h2>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>NSW Open Data — BOCSAR recorded crime by LGA and offence</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <KPICard label="Recorded Crime" value={s.crime_incidents?.value}
          delta={s.crime_incidents?.delta_pct} deltaUnit="% YoY"
          description={s.crime_incidents?.description} period={String(s.crime_incidents?.year ?? "")}
          accent="var(--red)" invertGood loading={loading} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <CrimeByOffenceChart />
        <CrimeTrendChart />
      </div>
    </div>
  );
}

// ── Root App ───────────────────────────────────────────────────────────────
const PAGES = {
  overview: Overview,
  labour:   LabourPage,
  cpi:      CPIPage,
  crime:    CrimePage,
  pipeline: PipelineLog,
};

export default function App() {
  const [activePage, setActivePage] = useState("overview");
  const PageComponent = PAGES[activePage] ?? Overview;

  return (
    <div className="layout">
      {/* Topbar */}
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: "auto" }}>
          {/* Logo mark */}
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="6" fill="var(--teal)" fillOpacity="0.15" />
            <rect x="4" y="14" width="4" height="6" rx="1" fill="var(--teal)" />
            <rect x="10" y="10" width="4" height="10" rx="1" fill="var(--teal)" fillOpacity="0.7" />
            <rect x="16" y="6" width="4" height="14" rx="1" fill="var(--teal)" fillOpacity="0.5" />
            <path d="M5 11 L11 8 L17 5" stroke="var(--amber)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
            NSW BI Dashboard
          </span>
          <span style={{ fontSize: 10, color: "var(--text-muted)", background: "var(--bg-secondary)", padding: "2px 6px", borderRadius: 4, fontFamily: "var(--font-mono)" }}>
            LIVE
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-muted)", fontSize: 12 }}>
          <MapPin size={12} />
          <span>New South Wales, Australia</span>
        </div>

        <a
          href="https://github.com/sarthak"
          target="_blank" rel="noreferrer"
          style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)", fontSize: 12, textDecoration: "none",
            background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6, padding: "4px 10px" }}
        >
          <Github size={13} />
          View on GitHub
        </a>
      </header>

      {/* Pipeline status bar */}
      <div style={{ gridColumn: "1 / -1" }}>
        <PipelineStatus />
      </div>

      {/* Sidebar */}
      <Sidebar active={activePage} onChange={setActivePage} />

      {/* Main content */}
      <main className="main-content">
        <PageComponent />
      </main>
    </div>
  );
}
