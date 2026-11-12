import { useState } from "react";
import { AlertTriangle, XOctagon } from "lucide-react";
import { useOnce } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton } from "./ChartCard";
import Pager from "./Pager";

const SEVERITIES = [["", "All"], ["error", "Errors"], ["warning", "Warnings"]];

/** Issues found by the validation layer before data reached the database. */
export default function QualityPanel() {
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("");
  const { data, loading, error } = useOnce(() => api.getQualityIssues(page, severity || undefined), [page, severity]);
  const issues = data?.issues ?? [];

  return (
    <ChartCard
      title="Data Quality Issues"
      subtitle="Checks run before every load: schema · duplicates · plausible range · outliers · missing periods"
      height={120} loading={loading && !data} error={error && !data ? error : null}
      empty={!loading && !issues.length} emptyMessage="No data-quality issues recorded — every load passed validation."
      controls={<>
        <div role="group" aria-label="Severity filter" className="range-picker">
          {SEVERITIES.map(([v, label]) => (
            <button key={label} type="button" aria-pressed={severity === v} className={severity === v ? "active" : ""}
              onClick={() => { setSeverity(v); setPage(1); }}>{label}</button>
          ))}
        </div>
        <ExportButton filename="data-quality-issues" rows={issues}
          columns={[{ key: "created_at", label: "When" }, { key: "pipeline", label: "Pipeline" }, { key: "severity", label: "Severity" },
            { key: "check", label: "Check" }, { key: "key", label: "Key" }, { key: "message", label: "Message" }]} />
      </>}
    >
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Severity</th><th>Pipeline</th><th>Check</th><th>Where</th><th>Detail</th></tr></thead>
          <tbody>
            {issues.map((i) => (
              <tr key={i.id}>
                <td>
                  <span className={`pill ${i.severity === "error" ? "pill-red" : "pill-amber"}`}>
                    {i.severity === "error" ? <XOctagon size={11} aria-hidden="true" /> : <AlertTriangle size={11} aria-hidden="true" />}
                    {i.severity}
                  </span>
                </td>
                <td>{i.display_name}</td>
                <td className="mono">{i.check}</td>
                <td className="mono">{i.key}</td>
                <td style={{ minWidth: 220 }}>{i.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} noun="issues" />
    </ChartCard>
  );
}
