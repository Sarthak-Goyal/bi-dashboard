import { FlaskConical } from "lucide-react";
import { usePolling } from "../hooks/useMetrics";
import { api } from "../utils/api";

const LABELS = {
  labour_force: "Labour Force", cpi: "CPI", building_approvals: "Building Approvals", crime: "Crime",
};

/** Honest provenance: shown whenever any dataset is synthetic sample data. */
export default function DataModeBanner({ onOpenPipeline }) {
  const { data } = usePolling(() => api.getDataMode(), 60_000);
  const sample = data?.sample_datasets ?? [];
  if (!sample.length) return null;
  return (
    <div role="status" className="banner">
      <FlaskConical size={15} aria-hidden="true" style={{ flexShrink: 0 }} />
      <span>
        <strong>Showing sample data</strong> for {sample.map((k) => LABELS[k] ?? k).join(", ")} — the live source couldn’t be reached,
        so generated placeholder numbers are displayed. They are not real statistics.{" "}
        <button type="button" className="link-btn" onClick={onOpenPipeline}>See why in the Pipeline Log</button>
      </span>
    </div>
  );
}
