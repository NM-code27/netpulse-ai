"use client";

import Link from "next/link";
import type { SiteOverview } from "@/lib/types";
import { RiskBar } from "./RiskBar";

const STATUS_ORDER: Record<string, number> = { critical: 0, warning: 1, healthy: 2, no_data: 3 };
const STATUS_COLOR: Record<string, string> = {
  critical: "var(--status-critical)", warning: "var(--status-warning)",
  healthy: "var(--status-good)", no_data: "var(--text-muted)",
};

export function SiteGrid({ sites }: { sites: SiteOverview[] }) {
  const sorted = [...sites].sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {sorted.map((site, i) => (
        <Link
          key={site.id}
          href={`/sites/${site.id}`}
          className="group relative overflow-hidden rounded-2xl border p-4 transition-all duration-200 hover:-translate-y-0.5"
          style={{
            background: "var(--surface)", borderColor: "var(--border)",
            boxShadow: "var(--shadow-sm)",
            animation: `fade-up 0.4s ease-out both`, animationDelay: `${Math.min(i * 25, 400)}ms`,
          }}
        >
          <span
            className="absolute inset-x-0 top-0 h-1"
            style={{ background: STATUS_COLOR[site.status] }}
          />
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">{site.name}</span>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {site.region}
            </span>
          </div>

          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-2xl font-bold tabular">
              {site.latest_value !== null ? Math.round(site.latest_value) : "--"}
            </span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              ms app response
            </span>
          </div>

          <div className="mt-3">
            <div className="mb-1 text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
              Outage risk
            </div>
            <RiskBar score={site.risk_score} />
          </div>

          {site.lead_time_minutes !== null && (
            <div
              className="mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
              style={{ background: "var(--status-warning-soft)", color: "var(--status-warning)" }}
            >
              ~{site.lead_time_minutes} min warning
            </div>
          )}

          <div className="mt-3 flex items-center justify-between border-t pt-2 text-[11px]" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <span className="capitalize">{site.tier} tier</span>
            <span>{site.users ?? "--"} users</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
