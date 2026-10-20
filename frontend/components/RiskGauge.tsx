"use client";

function colorFor(score: number) {
  if (score >= 80) return "var(--status-critical)";
  if (score >= 55) return "var(--status-warning)";
  return "var(--status-good)";
}

export function RiskGauge({ score, size = 96 }: { score: number | null; size?: number }) {
  const value = score ?? 0;
  const stroke = size * 0.1;
  const r = size / 2 - stroke;
  const circumference = 2 * Math.PI * r;
  const sweep = 0.75; // 270-degree arc
  const arcLength = circumference * sweep;
  const offset = arcLength * (1 - value / 100);
  const color = colorFor(value);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(135deg)" }}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="var(--gridline)" strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-xl font-bold tabular" style={{ color }}>
          {score === null ? "--" : Math.round(score)}
        </span>
        <span className="text-[9px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          risk
        </span>
      </div>
    </div>
  );
}
