const BASE = import.meta.env.VITE_API_URL || "";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getSummary: () => apiFetch("/api/metrics/summary"),
  getUnemployment: (region = "NSW", months = 36) =>
    apiFetch(`/api/metrics/unemployment?region=${region}&months=${months}`),
  getUnemploymentCompare: () => apiFetch("/api/metrics/unemployment/compare"),
  getCPI: (quarters = 20) => apiFetch(`/api/metrics/cpi?quarters=${quarters}`),
  getCrimeByOffence: (year) =>
    apiFetch(`/api/metrics/crime/by-offence${year ? `?year=${year}` : ""}`),
  getCrimeTrend: (offence = "Theft") =>
    apiFetch(`/api/metrics/crime/trend?offence=${encodeURIComponent(offence)}`),
  getCrimeTopLGAs: (year) =>
    apiFetch(`/api/metrics/crime/top-lgas${year ? `?year=${year}` : ""}`),
  getPipelineStatus: () => apiFetch("/api/pipeline/status"),
  getPipelineHistory: () => apiFetch("/api/pipeline/history?limit=20"),
  triggerRefresh: (pipeline = "all") =>
    apiFetch(`/api/pipeline/refresh?pipeline=${pipeline}`, { method: "POST" }),
};
