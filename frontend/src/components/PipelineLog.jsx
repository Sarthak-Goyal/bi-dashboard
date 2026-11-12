import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";
import { formatDistanceToNow } from "date-fns";

const StatusBadge = ({ status }) => {
  const styles = {
    success:   { bg: "var(--green-dim)",  color: "var(--green)", icon: CheckCircle2 },
    failed:    { bg: "var(--red-dim)",    color: "var(--red)",   icon: XCircle },
    running:   { bg: "var(--amber-dim)",  color: "var(--amber)", icon: Loader2 },
    never_run: { bg: "rgba(0,0,0,0.2)",   color: "var(--text-muted)", icon: Clock },
  };
  const s = styles[status] || styles.never_run;
  const Icon = s.icon;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: s.bg, color: s.color, borderRadius: 5, padding: "3px 8px", fontSize: 11, fontFamily: "var(--font-mono)", fontWeight: 600 }}>
      <Icon size={11} />
      {status}
    </span>
  );
};

export default function PipelineLog() {
  const { data, loading } = usePolling(() => api.getPipelineHistory(), 10_000);
  const runs = data?.runs ?? [];

  return (
    <div style={{ animation: "fadeIn 0.4s ease both" }}>
      <h2 style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Pipeline Audit Log</h2>
      <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 24 }}>
        Every ETL run is recorded — status, records processed, duration, and errors.
      </p>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Pipeline", "Status", "Started", "Duration", "Fetched", "Inserted", "Error"].map(h => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", color: "var(--text-muted)", fontWeight: 600, letterSpacing: "0.06em", fontSize: 10, textTransform: "uppercase", fontFamily: "var(--font-display)", whiteSpace: "nowrap" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>Loading…</td></tr>
            ) : runs.map((run, i) => (
              <tr key={run.id} style={{ borderBottom: "1px solid var(--border)", background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                  {run.display_name}
                </td>
                <td style={{ padding: "10px 16px" }}>
                  <StatusBadge status={run.status} />
                </td>
                <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                  {run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true }) : "—"}
                </td>
                <td style={{ padding: "10px 16px", color: run.duration_seconds ? "var(--text-primary)" : "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  {run.duration_seconds !== null ? `${run.duration_seconds.toFixed(1)}s` : "—"}
                </td>
                <td style={{ padding: "10px 16px", color: "var(--teal)", fontFamily: "var(--font-mono)" }}>
                  {run.records_fetched?.toLocaleString() ?? "—"}
                </td>
                <td style={{ padding: "10px 16px", color: "var(--green)", fontFamily: "var(--font-mono)" }}>
                  {run.records_inserted?.toLocaleString() ?? "—"}
                </td>
                <td style={{ padding: "10px 16px", color: "var(--red)", fontSize: 11, maxWidth: 240 }}>
                  <span title={run.error_message}>{run.error_message ? run.error_message.slice(0, 60) + (run.error_message.length > 60 ? "…" : "") : ""}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
