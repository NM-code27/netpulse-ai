"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { MetricChart } from "@/components/MetricChart";

const METRIC_LABELS: Record<string, { title: string; unit: string; color: string; threshold?: number }> = {
  app_response_time_ms: { title: "Application response time", unit: "ms", color: "var(--series-blue)", threshold: 220 },
  latency_ms: { title: "WAN link latency", unit: "ms", color: "var(--series-orange)", threshold: 120 },
  packet_loss_pct: { title: "WAN link packet loss", unit: "%", color: "var(--series-red)" , threshold: 3 },
  jitter_ms: { title: "WAN link jitter", unit: "ms", color: "var(--series-aqua)", threshold: 10 },
  bandwidth_util_pct: { title: "WAN bandwidth utilization", unit: "%", color: "var(--series-yellow)", threshold: 90 },
  cpu_pct: { title: "Device CPU", unit: "%", color: "var(--series-violet)", threshold: 90 },
  resolution_time_ms: { title: "DNS resolution time", unit: "ms", color: "var(--series-magenta)", threshold: 150 },
  response_time_ms: { title: "App tier response time", unit: "ms", color: "var(--series-aqua)", threshold: 250 },
  status: { title: "Device status (1 = up, 0 = down)", unit: "", color: "var(--series-yellow)" },
};

export default function SiteDetailClient() {
  const params = useParams<{ id: string }>();
  const siteId = params.id;
  const { data } = useSWR(siteId ? ["site-detail", siteId] : null, () => api.siteDetail(siteId, 90), {
    refreshInterval: 5000,
  });

  if (!data) {
    return (
      <>
        <TopBar title="Site" />
        <div className="p-6" style={{ color: "var(--text-muted)" }}>Loading...</div>
      </>
    );
  }

  const siteSeries = data.series[data.site.id] || {};
  const extra = data.site.extra as { users?: number; apps?: string[] };

  return (
    <>
      <TopBar title={data.site.name} subtitle={`${data.site.region} · ${data.site.tier} tier · ${extra.users ?? "--"} users`} />
      <div className="flex flex-col gap-5 p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Object.entries(siteSeries).map(([metric, points]) => {
            const cfg = METRIC_LABELS[metric] || { title: metric, unit: "", color: "var(--series-blue)" };
            return <MetricChart key={metric} title={cfg.title} unit={cfg.unit} points={points} color={cfg.color} threshold={cfg.threshold} />;
          })}
        </div>

        {data.children.map((child) => {
          const childSeries = data.series[child.id] || {};
          if (Object.keys(childSeries).length === 0) return null;
          return (
            <div key={child.id}>
              <h3 className="mb-2 text-sm font-semibold">{child.name}</h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {Object.entries(childSeries).map(([metric, points]) => {
                  const cfg = METRIC_LABELS[metric] || { title: metric, unit: "", color: "var(--series-blue)" };
                  return <MetricChart key={metric} title={cfg.title} unit={cfg.unit} points={points} color={cfg.color} threshold={cfg.threshold} />;
                })}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
