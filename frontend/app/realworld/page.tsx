"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { MetricChart } from "@/components/MetricChart";
import type { RealWorldSource } from "@/lib/types";

function SourceCard({ source }: { source: RealWorldSource }) {
  if (!source.available) {
    return (
      <div className="rounded-2xl border p-5 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        {source.label}: unavailable ({source.reason})
      </div>
    );
  }

  const beats = source.model_beats_naive;

  return (
    <div
      className="overflow-hidden rounded-2xl border"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b p-4" style={{ borderColor: "var(--border)" }}>
        <div>
          <h3 className="text-sm font-bold">{source.label}</h3>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Real ping RTT to <code>{source.target}</code> &middot; {source.n_points} real 10-minute samples from
            real RIPE Atlas probes worldwide
          </p>
        </div>
      </div>

      <div className="p-4">
        <MetricChart
          title="Real round-trip time"
          unit="ms"
          points={(source.series || []).map((p) => ({ timestamp: p.timestamp, value: p.value }))}
          color="var(--series-aqua)"
        />
      </div>

      <div className="grid grid-cols-2 gap-px border-t sm:grid-cols-4" style={{ background: "var(--border)", borderColor: "var(--border)" }}>
        {[
          { label: "Real mean RTT", value: `${source.real_mean_rtt_ms} ms` },
          { label: "Real std dev", value: `${source.real_std_rtt_ms} ms` },
          { label: "Model MAE (held-out)", value: `${source.model_mae_ms} ms` },
          { label: "Naive-persistence MAE", value: `${source.naive_persistence_mae_ms} ms` },
        ].map((stat) => (
          <div key={stat.label} className="p-4" style={{ background: "var(--surface)" }}>
            <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>{stat.label}</div>
            <div className="mt-1 text-lg font-bold tabular">{stat.value}</div>
          </div>
        ))}
      </div>

      <div
        className="flex items-center gap-2 border-t px-4 py-3 text-xs font-medium"
        style={{
          borderColor: "var(--border)",
          background: beats ? "var(--status-good-soft)" : "var(--status-warning-soft)",
          color: beats ? "var(--status-good)" : "var(--status-warning)",
        }}
      >
        {beats
          ? "A freshly-trained model beat the naive \"predict no change\" baseline on this real series."
          : "On this real series, a freshly-trained model did not beat the naive baseline -- an honest result, reported as-is."}
      </div>
    </div>
  );
}

export default function RealWorldPage() {
  const { data, error } = useSWR("realworld", api.realworld);

  return (
    <>
      <TopBar title="Real-World Data" subtitle="Live validation against RIPE Atlas public internet measurements" />
      <div className="flex flex-col gap-6 p-6">
        {error && (
          <p className="text-sm" style={{ color: "var(--status-critical)" }}>
            No real-world data fetched yet. Run <code>python -m app.realworld.fetch_ripe_atlas</code> then{" "}
            <code>python -m app.realworld.validate</code> on the backend.
          </p>
        )}

        {data?.sources.map((s) => <SourceCard key={s.label} source={s} />)}
      </div>
    </>
  );
}
