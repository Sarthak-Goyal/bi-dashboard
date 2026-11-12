/**
 * Client-side CSV export. Values are quoted/escaped per RFC 4180 and a UTF-8
 * BOM is prepended so Excel opens accented characters correctly.
 *
 * columns: [{ key: "period", label: "Period" }, ...]   (label defaults to key)
 */
export function toCsv(rows, columns) {
  const cols = columns ?? Object.keys(rows[0] ?? {}).map((key) => ({ key }));
  const esc = (v) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = cols.map((c) => esc(c.label ?? c.key)).join(",");
  const body = rows.map((r) => cols.map((c) => esc(r[c.key])).join(","));
  return [header, ...body].join("\r\n");
}

export function downloadCsv(filename, rows, columns) {
  if (!rows?.length) return;
  const blob = new Blob(["\uFEFF" + toCsv(rows, columns)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const stamp = () => new Date().toISOString().slice(0, 10);
