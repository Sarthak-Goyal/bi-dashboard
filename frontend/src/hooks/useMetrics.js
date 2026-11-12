import { useState, useEffect, useCallback, useRef } from "react";

/**
 * usePolling — fetches data on mount and then every `intervalMs` milliseconds.
 * Returns { data, loading, error, refetch, lastUpdated }.
 */
export function usePolling(fetchFn, intervalMs = 30_000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timerRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await fetchFn();
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setLoading(true);
    fetchData();
    timerRef.current = setInterval(fetchData, intervalMs);
    return () => clearInterval(timerRef.current);
  }, [fetchData, intervalMs]);

  return { data, loading, error, refetch: fetchData, lastUpdated };
}

/**
 * useOnce — fetch exactly once on mount (no polling).
 */
export function useOnce(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFn();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchData(); }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * useHashPage — tiny hash router so each page has a shareable URL (#crime) and
 * the browser back button / refresh keep working.
 */
export function useHashPage(valid, fallback = "overview") {
  const read = () => {
    const h = window.location.hash.replace(/^#\/?/, "");
    return valid.includes(h) ? h : fallback;
  };
  const [page, setPage] = useState(read);
  useEffect(() => {
    const onHash = () => setPage(read());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const go = useCallback((next) => { window.location.hash = next; }, []);
  return [page, go];
}
