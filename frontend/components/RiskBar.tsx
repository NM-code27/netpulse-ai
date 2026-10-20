function colorFor(score: number) {
  if (score >= 80) return "var(--status-critical)";
  if (score >= 55) return "var(--status-warning)";
  return "var(--status-good)";
}

export function RiskBar({ score }: { score: number | null }) {
  const value = score ?? 0;
  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1.5 w-full overflow-hidden rounded-full"
        style={{ background: "var(--gridline)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, value)}%`, background: colorFor(value) }}
        />
      </div>
      <span className="w-9 shrink-0 text-right text-xs tabular" style={{ color: "var(--text-secondary)" }}>
        {score === null ? "--" : Math.round(score)}
      </span>
    </div>
  );
}
