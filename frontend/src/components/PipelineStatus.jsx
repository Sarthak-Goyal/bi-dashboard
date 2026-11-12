import { useState } from "react";
import { RefreshCw, CheckCircle2, XCircle, Loader2, AlertCircle } from "lucide-react";
import { api } from "../utils/api";
import { usePolling } from "../hooks/useMetrics";
import { formatDistanceToNow } from "date-fns";

const STAGES = ["Fetch", "Transform", "Validate", "Load", "Serve"];

const statusColour = (s) => ({
  success: "var(--green)",
  failed: "var(--red)",
  running: "var(--amber)",
  never_run: "var(--text-muted)",
  initialising: "var(--amber)",
}[s] || "var(--text-muted)");

const StatusIcon = ({ status, size = 14 }) => {
  const props = { size, strokeWidth: 2 };
  if (status === "success")  return <CheckCircle2 {...props} color="var(--green)" />;
  if (status === "failed")   return <XCircle {...props} color="var(--red)" />;
  if (status === "running")  return <Loader2 {...props} color="var(--amber)" className="spin" />;
  return <AlertCircle {...props} color="var(--text-muted)" />;
};

export default function PipelineStatus() {
  const { data, loading, refetch } = usePolling(() => api.getPipelineStatus(), 15_000);
  const [triggering, setTriggering] = useState(false);
  const [refreshError, setRefreshError] = useState(null);

  async function handleRefresh() {
    setTriggering(true);
    setRefreshError(null);
    try {
      await api.triggerRefresh("all");
    } catch (e) {
      setRefreshError(e.status === 401 ? "Refresh needs an API key (set VITE_API_KEY)" : "Couldn’t trigger refresh");
    }
    setTimeout(() => { setTriggering(false); refetch(); }, 2000);
  }

  const pipelines = data?.pipelines ?? [];
  const health = data?.overall_health ?? "initialising";

  return (
    <div className="statusbar">
      {/* Pipeline flow diagram */}
      <div className="pipeline-stages" style={{ display: "flex", alignItems: "center", gap: 0, flexShrink: 0 }}>
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginRight: 10, fontFamily: "var(--font-mono)", letterSpacing: "0.05em" }}>
          PIPELINE
        </span>
        {STAGES.map((stage, i) => (
          <div key={stage} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              position: "relative",
              overflow: "hidden",
              background: health === "healthy" ? "var(--teal-dim)" : health === "degraded" ? "var(--red-dim)" : "var(--amber-dim)",
              border: `1px solid ${health === "healthy" ? "var(--border-accent)" : health === "degraded" ? "rgba(255,77,106,0.3)" : "rgba(245,166,35,0.3)"}`,
              borderRadius: 4,
              padding: "3px 10px",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: health === "healthy" ? "var(--teal)" : health === "degraded" ? "var(--red)" : "var(--amber)",
              fontWeight: 600,
              letterSpacing: "0.03em",
            }}>
              {/* Animated flow shimmer */}
              {health === "healthy" && (
                <div style={{
                  position: "absolute", inset: 0,
                  background: "linear-gradient(90deg, transparent, rgba(0,212,200,0.2), transparent)",
                  backgroundSize: "200% 100%",
                  animation: `shimmer ${1.5 + i * 0.3}s linear infinite`,
                  animationDelay: `${i * 0.2}s`,
                }} />
              )}
              {stage}
            </div>
            {i < STAGES.length - 1 && (
              <svg width="20" height="12" viewBox="0 0 20 12">
                <path d="M2 6 L14 6" stroke={health === "healthy" ? "var(--teal)" : "var(--text-muted)"} strokeWidth="1.5" strokeDasharray="3,2" />
                <path d="M12 3 L17 6 L12 9" fill="none" stroke={health === "healthy" ? "var(--teal)" : "var(--text-muted)"} strokeWidth="1.5" />
              </svg>
            )}
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="pipeline-stages" style={{ width: 1, height: 28, background: "var(--border)", flexShrink: 0 }} />

      {/* Individual pipeline statuses */}
      <div style={{ display: "flex", gap: 16, alignItems: "center", flex: 1, flexWrap: "wrap" }}>
        {loading ? (
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Loading pipeline status…</span>
        ) : pipelines.map((p) => (
          <div key={p.pipeline} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <StatusIcon status={p.status} />
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", fontFamily: "var(--font-mono)", lineHeight: 1 }}>
                {p.display_name}
                {p.mode === "sample" && <span className="pill pill-amber" style={{ marginLeft: 6 }}>sample</span>}
              </div>
              {p.last_run && (
                <div className="pipe-meta" style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>
                  {formatDistanceToNow(new Date(p.last_run), { addSuffix: true })}
                  {p.records_inserted > 0 && ` · ${p.records_inserted.toLocaleString()} rows`}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Refresh button */}
      <button
        type="button"
        onClick={handleRefresh}
        disabled={triggering}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "var(--teal-dim)", border: "1px solid var(--border-accent)",
          borderRadius: 6, padding: "5px 12px", cursor: triggering ? "not-allowed" : "pointer",
          color: "var(--teal)", fontSize: 12, fontFamily: "var(--font-body)",
          opacity: triggering ? 0.6 : 1, transition: "opacity 0.2s",
          flexShrink: 0,
        }}
      >
        <RefreshCw size={12} aria-hidden="true" style={{ animation: triggering ? "spin 1s linear infinite" : "none" }} />
        {triggering ? "Triggering…" : "Refresh All"}
      </button>
      {refreshError && <span role="alert" style={{ fontSize: 11, color: "var(--amber)" }}>{refreshError}</span>}

    </div>
  );
}
