import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pager({ page, pages, total, onChange, noun = "rows" }) {
  return (
    <nav aria-label="Pagination" className="pager">
      <span>{total.toLocaleString()} {noun}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button type="button" className="icon-btn" onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft size={14} aria-hidden="true" />
        </button>
        <span className="mono" aria-live="polite">Page {page} of {pages}</span>
        <button type="button" className="icon-btn" onClick={() => onChange(page + 1)} disabled={page >= pages} aria-label="Next page">
          <ChevronRight size={14} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
