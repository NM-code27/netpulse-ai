"use client";

import { useRouter } from "next/navigation";
import type { SiteOverview } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  healthy: "var(--status-good)",
  warning: "var(--status-warning)",
  critical: "var(--status-critical)",
  no_data: "var(--text-muted)",
};

interface Props {
  sites: SiteOverview[];
}

export function NetworkMap({ sites }: Props) {
  const router = useRouter();
  const branches = sites.filter((s) => s.id !== "site-hq");

  const size = 640;
  const center = size / 2;
  const radius = size * 0.38;

  const nodes = branches.map((site, i) => {
    const angle = (i / branches.length) * Math.PI * 2 - Math.PI / 2;
    return {
      site,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  });

  return (
    <div
      className="relative overflow-hidden rounded-2xl border"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-md)" }}
    >
      <svg viewBox={`0 0 ${size} ${size}`} className="h-[420px] w-full" role="img" aria-label="Network topology map">
        <defs>
          <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.18" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </radialGradient>
          {nodes.map(({ site }) => (
            <linearGradient key={`grad-${site.id}`} id={`line-${site.id}`} gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={STATUS_COLOR[site.status]} stopOpacity="0.15" />
              <stop offset="100%" stopColor={STATUS_COLOR[site.status]} stopOpacity="0.85" />
            </linearGradient>
          ))}
        </defs>

        <circle cx={center} cy={center} r={radius * 0.92} fill="url(#hubGlow)" />

        {/* Links */}
        {nodes.map(({ site, x, y }, i) => {
          const atRisk = site.status === "warning" || site.status === "critical";
          return (
            <g key={site.id}>
              <line
                x1={center} y1={center} x2={x} y2={y}
                stroke={`url(#line-${site.id})`}
                strokeWidth={atRisk ? 2.5 : 1.5}
              />
              {atRisk && (
                <line
                  x1={center} y1={center} x2={x} y2={y}
                  stroke={STATUS_COLOR[site.status]}
                  strokeWidth={2.5}
                  strokeDasharray="6 10"
                  strokeLinecap="round"
                  opacity={0.9}
                  style={{ animation: `flow-dash 1.1s linear infinite`, animationDelay: `${i * 0.05}s` }}
                />
              )}
            </g>
          );
        })}

        {/* Hub */}
        <g style={{ animation: "float-soft 6s ease-in-out infinite" }}>
          <circle cx={center} cy={center} r={22} fill="var(--accent-gradient)" />
          <circle cx={center} cy={center} r={22} fill="var(--accent)" />
          <circle cx={center} cy={center} r={22} fill="none" stroke="white" strokeOpacity={0.35} strokeWidth={2} />
          <text x={center} y={center + 40} textAnchor="middle" fontSize="12" fontWeight={600} fill="var(--text-primary)">
            HQ
          </text>
        </g>

        {/* Branch nodes */}
        {nodes.map(({ site, x, y }) => {
          const color = STATUS_COLOR[site.status];
          const atRisk = site.status === "warning" || site.status === "critical";
          return (
            <g
              key={site.id}
              transform={`translate(${x}, ${y})`}
              className="cursor-pointer"
              onClick={() => router.push(`/sites/${site.id}`)}
            >
              {atRisk && (
                <circle r={9} fill="none" stroke={color} strokeWidth={2} style={{ animation: "pulse-ring 1.8s ease-out infinite", transformOrigin: "center" }} />
              )}
              <circle r={8} fill={color} stroke="var(--surface)" strokeWidth={2.5} />
              <title>{`${site.name} -- ${site.status} (risk ${site.risk_score ?? "--"})`}</title>
            </g>
          );
        })}

        {/* Labels -- only for at-risk sites, to keep the map legible */}
        {nodes.filter(({ site }) => site.status === "warning" || site.status === "critical").map(({ site, x, y }) => {
          const labelX = center + (x - center) * 1.14;
          const labelY = center + (y - center) * 1.14;
          return (
            <text
              key={`label-${site.id}`}
              x={labelX} y={labelY}
              textAnchor={labelX > center ? "start" : labelX < center ? "end" : "middle"}
              fontSize="11" fontWeight={600}
              fill={STATUS_COLOR[site.status]}
            >
              {site.name.replace(" Branch", "")}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
