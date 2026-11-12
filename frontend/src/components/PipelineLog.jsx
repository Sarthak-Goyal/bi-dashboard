import { useState } from "react";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";
import ChartCard, { ExportButton } from "./ChartCard";
import Pager from "./Pager";
import QualityPanel from "./QualityPanel";

const STATUS = {
  success: { icon: CheckCircle2, colour: "var(--green)" },
  failed: { icon: XCircle, colour: "var(--red)" },
  running: { icon: Loader2, colour: "var(--amber)" },
};

export default function PipelineLog() {
  const [page, setPage] = useState(1);
  const { data, loading, error } = usePolling(() => api.getPipelineHistory(page, 10), 20_000, [page]);
  const runs = data?.runs ?? [];

  return (
    <div className="page">
      <div>
        <h2 className="page-title">Pipeline Log</h2>
        <p className="page-sub">Audit trail of every ETL run: incremental loads, data-quality results and failures</p>
      </div>

      <ChartCard
        title="ETL Run History" subtitle="Newest first. Incremental loads only insert new periods and update revised values."
        height={160} loading={loading && !data} error={error && !data ? error : null} empty={!loading && !runs.length}
        controls={<ExportButton filename="pipeline-runs" rows={runs}
          columns={[{ key: "started_at", label: "Started" }, { key: "display_name", label: "Pipeline" }, { key: "status", label: "Status" },
            { key: "mode", label: "Mode" }, { key: "watermark", label: "Watermark" }, { key: "records_fetched", label: "Fetched" },
            { key: "records_inserted", label: "Inserted" }, { key: "records_updated", label: "Updated" },
            { key: "records_skipped", label: "Skipped" }, { key: "quality_issues", label: "Quality issues" }, { key: "error_message", label: "Error" }]} />}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr><th>Pipeline</th><th>Status</th><th>Source</th><th>Started</th><th>Watermark</th>
                <th className="num">Fetched</th><th className="num">New</th><th className="num">Revised</th><th className="num">Dropped</th><th className="num">Issues</th></tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const s = STATUS[r.status] ?? STATUS.running;
                const Icon = s.icon;
                return (
                  <tr key={r.id}>
                    <td>{r.display_name}</td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: s.colour }}>
                        <Icon size={13} aria-hidden="true" className={r.status === "running" ? "spin" : undefined} />{r.status}
                      </span>
                      {r.error_message && <div title={r.error_message} style={{ fontSize: 11, color: "var(--text-muted)", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.error_message}</div>}
                    </td>
                    <td>{r.mode ? <span className={`pill ${r.mode === "sample" ? "pill-amber" : "pill-green"}`}>{r.mode}</span> : "—"}</td>
                    <td className="mono">{r.started_at ? format(new Date(r.started_at), "d MMM, HH:mm:ss") : "—"}</td>
                    <td className="mono">{r.watermark ?? "—"}</td>
                    <td className="num mono">{r.records_fetched}</td>
                    <td className="num mono">{r.records_inserted}</td>
                    <td className="num mono">{r.records_updated}</td>
                    <td className="num mono">{r.records_skipped}</td>
                    <td className="num mono">{r.quality_issues}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <Pager page={data?.page ?? 1} pages={data?.pages ?? 1} total={data?.total ?? 0} onChange={setPage} noun="runs" />
      </ChartCard>

      <QualityPanel />
    </div>
  );
}
