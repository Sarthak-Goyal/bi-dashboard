const BASE = import.meta.env.VITE_API_URL || "";
// NOTE: anything in a browser bundle is public. This header demonstrates the
// pattern for protecting write endpoints; real per-user auth would use sessions/OAuth.
const API_KEY = import.meta.env.VITE_API_KEY || "";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (API_KEY && options.method === "POST") headers["X-API-Key"] = API_KEY;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, `API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

const qs = (params) => {
  const p = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return p.length ? "?" + p.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&") : "";
};

export const api = {
  getSummary: () => apiFetch("/api/metrics/summary"),
  getDataMode: () => apiFetch("/api/metrics/data-mode"),
  getUnemploymentCompare: (months = 24) => apiFetch(`/api/metrics/unemployment/compare${qs({ months })}`),
  getCPI: (quarters = 20) => apiFetch(`/api/metrics/cpi${qs({ quarters })}`),
  getHousingLabour: (months = 36) => apiFetch(`/api/metrics/housing-labour${qs({ months })}`),
  getCrimeByOffence: (year) => apiFetch(`/api/metrics/crime/by-offence${qs({ year })}`),
  getCrimeOffences: () => apiFetch("/api/metrics/crime/offences"),
  getCrimeTrend: (offence = "Theft", years = 0) => apiFetch(`/api/metrics/crime/trend${qs({ offence, years })}`),
  getCrimeByLGA: (offence = "All") => apiFetch(`/api/metrics/crime/by-lga${qs({ offence })}`),
  getPipelineStatus: () => apiFetch("/api/pipeline/status"),
  getPipelineHistory: (page = 1, pageSize = 10) => apiFetch(`/api/pipeline/history${qs({ page, page_size: pageSize })}`),
  getQualityIssues: (page = 1, severity) => apiFetch(`/api/pipeline/quality${qs({ page, page_size: 8, severity })}`),
  triggerRefresh: (pipeline = "all") => apiFetch(`/api/pipeline/refresh${qs({ pipeline })}`, { method: "POST" }),
};
