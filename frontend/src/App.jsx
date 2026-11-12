import { useEffect, useRef, useState } from "react";
import { MapPin, Github, Menu, X } from "lucide-react";
import { usePolling, useHashPage } from "./hooks/useMetrics";
import { api } from "./utils/api";
import Sidebar, { NAV } from "./components/Sidebar";
import PipelineStatus from "./components/PipelineStatus";
import DataModeBanner from "./components/DataModeBanner";
import KPICard from "./components/KPICard";
import UnemploymentChart from "./components/UnemploymentChart";
import CPIChart from "./components/CPIChart";
import HousingChart from "./components/HousingChart";
import CrimeMap from "./components/CrimeMap";
import { CrimeByOffenceChart, CrimeTrendChart } from "./components/CrimeCharts";
import PipelineLog from "./components/PipelineLog";

const REPO_URL = "https://github.com/Sarthak-Goyal/bi-dashboard";

function PageHeader({ title, subtitle }) {
  return (
    <div>
      <h2 className="page-title">{title}</h2>
      <p className="page-sub">{subtitle}</p>
    </div>
  );
}

function useSummary() {
  const { data, loading } = usePolling(() => api.getSummary(), 30_000);
  return { s: data ?? {}, loading: loading && !data };
}

// ── Overview ───────────────────────────────────────────────────────────────
function Overview() {
  const { s, loading } = useSummary();
  return (
    <div className="page">
      <PageHeader title="NSW Economic Dashboard" subtitle="Incremental data pipeline · ABS Labour Force, CPI, Building Approvals & NSW Open Data" />
      <div className="kpi-grid">
        <KPICard label="Unemployment Rate" value={s.unemployment_rate?.value} unit="%" delta={s.unemployment_rate?.delta} deltaUnit=" pts"
          description={s.unemployment_rate?.description} period={s.unemployment_rate?.period} accent="var(--teal)" invertGood loading={loading} />
        <KPICard label="Participation Rate" value={s.participation_rate?.value} unit="%" delta={s.participation_rate?.delta} deltaUnit=" pts"
          description={s.participation_rate?.description} period={s.participation_rate?.period} accent="var(--green)" loading={loading} />
        <KPICard label="CPI Annual Change" value={s.cpi_annual_change?.value} unit="%"
          description={s.cpi_annual_change?.description} period={s.cpi_annual_change?.period} accent="var(--amber)" invertGood loading={loading} />
        <KPICard label="Dwelling Approvals" integer value={s.building_approvals?.value} delta={s.building_approvals?.delta_pct} deltaUnit="% MoM"
          description={s.building_approvals?.description} period={s.building_approvals?.period} accent="#a78bfa" loading={loading} />
        <KPICard label="Recorded Crime" value={s.crime_incidents?.value} delta={s.crime_incidents?.delta_pct} deltaUnit="%"
          description={s.crime_incidents?.description} period={String(s.crime_incidents?.year ?? "")} accent="var(--red)" invertGood loading={loading} />
      </div>
      <div className="grid-2"><UnemploymentChart /><CPIChart /></div>
      <div className="grid-2"><CrimeByOffenceChart /><CrimeTrendChart /></div>
    </div>
  );
}

// ── Labour Force ───────────────────────────────────────────────────────────
function LabourPage() {
  const { s, loading } = useSummary();
  const code = { fontFamily: "var(--font-mono)", fontSize: 11, background: "var(--bg-secondary)", padding: "1px 5px", borderRadius: 3 };
  return (
    <div className="page">
      <PageHeader title="Labour Force" subtitle="ABS Labour Force Survey — seasonally adjusted monthly data" />
      <div className="kpi-grid">
        <KPICard label="Unemployment Rate" value={s.unemployment_rate?.value} unit="%" delta={s.unemployment_rate?.delta} deltaUnit=" pts"
          description="NSW, seasonally adjusted" period={s.unemployment_rate?.period} accent="var(--teal)" invertGood loading={loading} />
        <KPICard label="Participation Rate" value={s.participation_rate?.value} unit="%" delta={s.participation_rate?.delta} deltaUnit=" pts"
          description="NSW, seasonally adjusted" period={s.participation_rate?.period} accent="var(--green)" loading={loading} />
      </div>
      <UnemploymentChart />
      <div className="card">
        <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 14, marginBottom: 8 }}>About this data</h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
          Sourced from the <strong style={{ color: "var(--teal)" }}>ABS Labour Force Survey</strong> via the ABS SDMX Data API (<code style={code}>api.data.abs.gov.au</code>),
          dataflow <code style={code}>LF</code>: unemployment rate and participation rate, seasonally adjusted, NSW and Australia, monthly.
          The pipeline is incremental — it remembers the latest period it stored and re-fetches only the most recent months (to catch ABS revisions).
        </p>
      </div>
    </div>
  );
}

// ── CPI ────────────────────────────────────────────────────────────────────
function CPIPage() {
  const { s, loading } = useSummary();
  return (
    <div className="page">
      <PageHeader title="Cost of Living" subtitle="ABS Consumer Price Index — Sydney, all groups, quarterly" />
      <div className="kpi-grid">
        <KPICard label="CPI Annual Change" value={s.cpi_annual_change?.value} unit="%" description="All groups, Sydney"
          period={s.cpi_annual_change?.period} accent="var(--amber)" invertGood loading={loading} />
        <KPICard label="CPI Index" value={s.cpi_annual_change?.index_value} description="All groups index value"
          period={s.cpi_annual_change?.period} accent="var(--teal)" loading={loading} />
      </div>
      <CPIChart />
    </div>
  );
}

// ── Housing (multi-source join) ────────────────────────────────────────────
function HousingPage() {
  const { s, loading } = useSummary();
  return (
    <div className="page">
      <PageHeader title="Housing & Labour Market" subtitle="Building approvals joined with unemployment and CPI — three sources, one timeline" />
      <div className="kpi-grid">
        <KPICard label="Dwelling Approvals" integer value={s.building_approvals?.value} delta={s.building_approvals?.delta_pct} deltaUnit="% MoM"
          description={s.building_approvals?.description} period={s.building_approvals?.period} accent="#a78bfa" loading={loading} />
        <KPICard label="Unemployment Rate" value={s.unemployment_rate?.value} unit="%" delta={s.unemployment_rate?.delta} deltaUnit=" pts"
          description="NSW, seasonally adjusted" period={s.unemployment_rate?.period} accent="var(--teal)" invertGood loading={loading} />
        <KPICard label="CPI Annual Change" value={s.cpi_annual_change?.value} unit="%" description="All groups, Sydney"
          period={s.cpi_annual_change?.period} accent="var(--amber)" invertGood loading={loading} />
      </div>
      <HousingChart />
    </div>
  );
}

// ── Crime ──────────────────────────────────────────────────────────────────
function CrimePage() {
  const { s, loading } = useSummary();
  return (
    <div className="page">
      <PageHeader title="NSW Crime Statistics" subtitle="NSW Open Data — recorded crime by LGA and offence" />
      <div className="kpi-grid">
        <KPICard label="Recorded Crime" value={s.crime_incidents?.value} delta={s.crime_incidents?.delta_pct} deltaUnit="% YoY"
          description={s.crime_incidents?.description} period={String(s.crime_incidents?.year ?? "")} accent="var(--red)" invertGood loading={loading} />
      </div>
      <CrimeMap />
      <div className="grid-2"><CrimeByOffenceChart /><CrimeTrendChart /></div>
    </div>
  );
}

const PAGES = { overview: Overview, labour: LabourPage, cpi: CPIPage, housing: HousingPage, crime: CrimePage, pipeline: PipelineLog };
const PAGE_IDS = NAV.map((n) => n.id);

function ModeBadge() {
  const { data } = usePolling(() => api.getDataMode(), 60_000);
  const mode = data?.overall;
  const map = {
    live: ["LIVE", "pill-green"], sample: ["SAMPLE DATA", "pill-amber"], mixed: ["MIXED", "pill-amber"],
  };
  const [label, cls] = map[mode] ?? ["LOADING", "pill-muted"];
  return <span className={`pill ${cls}`} title="Whether the numbers come from the live sources or generated sample data">{label}</span>;
}

export default function App() {
  const [page, go] = useHashPage(PAGE_IDS);
  const [navOpen, setNavOpen] = useState(false);
  const mainRef = useRef(null);
  const PageComponent = PAGES[page] ?? Overview;

  useEffect(() => { window.scrollTo({ top: 0 }); setNavOpen(false); }, [page]);

  return (
    <div className="layout">
      <a href="#main-content" className="skip-link" onClick={(e) => { e.preventDefault(); mainRef.current?.focus(); }}>Skip to content</a>

      <header className="topbar">
        <button type="button" className="menu-btn" aria-label={navOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navOpen} aria-controls="primary-nav" onClick={() => setNavOpen((o) => !o)}>
          {navOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: "auto", minWidth: 0 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
            <rect width="24" height="24" rx="6" fill="var(--teal)" fillOpacity="0.15" />
            <rect x="4" y="14" width="4" height="6" rx="1" fill="var(--teal)" />
            <rect x="10" y="10" width="4" height="10" rx="1" fill="var(--teal)" fillOpacity="0.7" />
            <rect x="16" y="6" width="4" height="14" rx="1" fill="var(--teal)" fillOpacity="0.5" />
            <path d="M5 11 L11 8 L17 5" stroke="var(--amber)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span className="brand">NSW BI Dashboard</span>
          <ModeBadge />
        </div>

        <div className="hide-md" style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)", fontSize: 12 }}>
          <MapPin size={12} aria-hidden="true" />
          <span>New South Wales, Australia</span>
        </div>

        <a href={REPO_URL} target="_blank" rel="noreferrer" className="gh-link" aria-label="View source on GitHub">
          <Github size={14} aria-hidden="true" />
          <span className="hide-sm">View on GitHub</span>
        </a>
      </header>

      <div style={{ gridColumn: "1 / -1" }}>
        <PipelineStatus />
      </div>

      <Sidebar active={page} onChange={go} open={navOpen} onClose={() => setNavOpen(false)} />

      <main id="main-content" ref={mainRef} tabIndex={-1} className="main-content">
        <DataModeBanner onOpenPipeline={() => go("pipeline")} />
        <PageComponent />
      </main>
    </div>
  );
}
