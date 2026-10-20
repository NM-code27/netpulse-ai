"use client";

import useSWR from "swr";
import Link from "next/link";
import { AlertTriangle, Gauge, Network, ShieldCheck, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { HeroStat } from "@/components/HeroStat";
import { NetworkMap } from "@/components/NetworkMap";
import { SiteGrid } from "@/components/SiteGrid";
import { ScenarioControls } from "@/components/ScenarioControls";
import { AlertCard } from "@/components/AlertCard";

export default function OverviewPage() {
  const { data: sites } = useSWR("overview", api.overview, { refreshInterval: 5000 });
  const { data: alerts, mutate: refetchAlerts } = useSWR(
    ["alerts", "unresolved"], () => api.alerts(false, 5), { refreshInterval: 5000 }
  );

  const total = sites?.length ?? 0;
  const critical = sites?.filter((s) => s.status === "critical").length ?? 0;
  const warning = sites?.filter((s) => s.status === "warning").length ?? 0;
  const healthy = sites?.filter((s) => s.status === "healthy").length ?? 0;
  const scored = sites?.filter((s) => s.risk_score !== null) ?? [];
  const avgRisk = scored.length
    ? Math.round(scored.reduce((a, s) => a + (s.risk_score ?? 0), 0) / scored.length)
    : null;

  return (
    <>
      <TopBar title="Network Overview" subtitle="20 branch offices + HQ datacenter, live synthetic telemetry" />
      <div className="flex flex-col gap-6 p-6">
        <div className="flex flex-col gap-3 sm:flex-row">
          <HeroStat label="Sites" value={total} icon={Network} color="var(--accent)" bg="var(--accent-soft)" />
          <HeroStat label="Healthy" value={healthy} icon={ShieldCheck} color="var(--status-good)" bg="var(--status-good-soft)" />
          <HeroStat label="Warning" value={warning} icon={ShieldAlert} color="var(--status-warning)" bg="var(--status-warning-soft)" />
          <HeroStat label="Critical" value={critical} icon={AlertTriangle} color="var(--status-critical)" bg="var(--status-critical-soft)" />
          <HeroStat label="Avg. outage risk" value={avgRisk ?? "--"} hint="0-100 across all sites" icon={Gauge} color="var(--series-violet)" bg="rgba(91,76,207,0.12)" />
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
          {sites ? <NetworkMap sites={sites} /> : (
            <div className="flex h-[420px] items-center justify-center rounded-2xl border" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              Loading network map...
            </div>
          )}
          <ScenarioControls />
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold">Site health</h2>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Click a site for detailed metrics
            </span>
          </div>
          {sites ? <SiteGrid sites={sites} /> : <p style={{ color: "var(--text-muted)" }}>Loading...</p>}
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold">Recent alerts</h2>
            <Link href="/alerts" className="text-xs font-medium" style={{ color: "var(--accent)" }}>
              View all
            </Link>
          </div>
          <div className="space-y-2">
            {alerts && alerts.length > 0 ? (
              alerts.map((a) => <AlertCard key={a.id} alert={a} onResolved={() => refetchAlerts()} />)
            ) : (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                No active alerts. The network is healthy -- try injecting a fault scenario above.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
