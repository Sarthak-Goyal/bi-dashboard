import { TrendingUp, TrendingDown, Minus } from "lucide-react";

function Delta({ value, unit = "", invertGood = false }) {
  if (value === null || value === undefined) return null;
  const isPositive = value > 0;
  const isGood = invertGood ? !isPositive : isPositive;
  const colour = value === 0 ? "var(--text-muted)" : isGood ? "var(--green)" : "var(--red)";
  const Icon = value === 0 ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 3, color: colour, fontSize: 12, fontFamily: "var(--font-mono)" }}>
      <Icon size={12} />
      {isPositive ? "+" : ""}{value.toFixed(2)}{unit}
    </span>
  );
}

/**
 * KPICard — headline metric card.
 *
 * Props:
 *   label        string   — card title
 *   value        number   — main figure
 *   unit         string   — suffix (%, pts, …)
 *   delta        number   — change vs previous period
 *   deltaUnit    string   — delta suffix
 *   description  string   — sub-label
 *   period       string   — data period
 *   accent       string   — CSS colour var for left border
 *   invertGood   bool     — if true, positive delta = bad (e.g. unemployment)
 *   loading      bool
 *   icon         node
 */
export default function KPICard({
  label, value, unit = "", delta = null, deltaUnit = "",
  description, period, accent = "var(--teal)", invertGood = false,
  loading = false, icon, large = false,
}) {
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderLeft: `3px solid ${accent}`,
      borderRadius: 12,
      padding: large ? "22px 24px" : "18px 20px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      transition: "border-color 0.2s, transform 0.15s",
      animation: "fadeIn 0.4s ease both",
      cursor: "default",
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.borderTopColor = "rgba(255,255,255,0.12)"; }}
      onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.borderTopColor = "var(--border)"; }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: "var(--text-secondary)", textTransform: "uppercase", fontFamily: "var(--font-display)" }}>
          {label}
        </span>
        {icon && (
          <span style={{ color: accent, opacity: 0.7 }}>{icon}</span>
        )}
      </div>

      {/* Main value */}
      {loading ? (
        <div style={{ height: large ? 44 : 36, background: "linear-gradient(90deg, var(--bg-card-hover) 25%, var(--bg-secondary) 50%, var(--bg-card-hover) 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.5s infinite", borderRadius: 6 }} />
      ) : (
        <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
          <span style={{
            fontFamily: "var(--font-mono)",
            fontSize: large ? 38 : 30,
            fontWeight: 700,
            lineHeight: 1,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
          }}>
            {value !== null && value !== undefined
              ? typeof value === "number" && value > 10000
                ? value.toLocaleString()
                : typeof value === "number"
                  ? value.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
                  : value
              : "—"}
          </span>
          {unit && (
            <span style={{ fontSize: 14, color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
              {unit}
            </span>
          )}
        </div>
      )}

      {/* Delta + description row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 4 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {delta !== null && <Delta value={delta} unit={deltaUnit} invertGood={invertGood} />}
          {description && (
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{description}</span>
          )}
        </div>
        {period && (
          <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)", background: "var(--bg-secondary)", padding: "2px 6px", borderRadius: 4 }}>
            {period}
          </span>
        )}
      </div>
    </div>
  );
}
