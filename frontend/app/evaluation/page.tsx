"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { StatTile } from "@/components/StatTile";

const METRIC_DISPLAY: Record<string, string> = {
  latency_ms: "WAN latency (ms)",
  packet_loss_pct: "WAN packet loss (%)",
  jitter_ms: "WAN jitter (ms)",
  bandwidth_util_pct: "WAN bandwidth utilization (%)",
  cpu_pct: "Device CPU (%)",
  resolution_time_ms: "DNS resolution time (ms)",
  response_time_ms: "App tier response time (ms)",
  app_response_time_ms: "Site application response time (ms)",
};

export default function EvaluationPage() {
  const { data, error } = useSWR("evaluation", api.evaluation);

  return (
    <>
      <TopBar
        title="Model Evaluation"
        subtitle="Held-out, chronologically-split backtest results -- no future information leaks into training"
      />
      <div className="flex flex-col gap-6 p-6">
        {error && (
          <p className="text-sm" style={{ color: "var(--status-critical)" }}>
            No training report found yet. Run <code>python -m app.ml.train</code> on the backend.
          </p>
        )}

        {data && (
          <>
            <div className="flex flex-col gap-3 sm:flex-row">
              <StatTile
                label="Root-cause top-1 accuracy"
                value={data.root_cause.top1_accuracy !== null ? `${Math.round(data.root_cause.top1_accuracy * 100)}%` : "--"}
                hint={`${data.root_cause.total_faults_evaluated} held-out faults`}
              />
              <StatTile
                label="Root-cause top-3 accuracy"
                value={data.root_cause.top3_accuracy !== null ? `${Math.round(data.root_cause.top3_accuracy * 100)}%` : "--"}
              />
              <StatTile label="Metric families modeled" value={Object.keys(data.metrics).length} />
            </div>

            <div>
              <h2 className="mb-3 text-sm font-bold">Forecasting + predictive-risk classifiers</h2>
              <div className="overflow-x-auto rounded-2xl border" style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)" }}>
                      <th className="px-3 py-2 text-left" style={{ color: "var(--text-muted)" }}>Metric</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>Forecast MAE</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>Forecast RMSE</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>10 min P/R</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>20 min P/R</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>30 min P/R</th>
                      <th className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>False alarms/entity-day</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.metrics).map(([metric, m]) => (
                      <tr key={metric} className="border-t" style={{ borderColor: "var(--border)" }}>
                        <td className="px-3 py-2">{METRIC_DISPLAY[metric] || metric}</td>
                        <td className="px-3 py-2 text-right tabular">{m.forecast.mae}</td>
                        <td className="px-3 py-2 text-right tabular">{m.forecast.rmse}</td>
                        {["10", "20", "30"].map((h) => {
                          const hm = m.risk_classifiers[h];
                          return (
                            <td key={h} className="px-3 py-2 text-right tabular">
                              {hm ? `${hm.precision.toFixed(2)} / ${hm.recall.toFixed(2)}` : "--"}
                            </td>
                          );
                        })}
                        <td className="px-3 py-2 text-right tabular">{m.false_alarms_per_entity_day ?? "--"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-[11px]" style={{ color: "var(--text-muted)" }}>
                P/R = precision / recall for &quot;will this metric breach its threshold within N minutes&quot;,
                evaluated on the held-out test split. Precision naturally falls at longer horizons -- predicting
                further into the future is a harder problem.
              </p>
            </div>

            <div>
              <h2 className="mb-3 text-sm font-bold">Root-cause examples (held-out faults)</h2>
              <div className="overflow-x-auto rounded-2xl border" style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)" }}>
                      <th className="px-3 py-2 text-left" style={{ color: "var(--text-muted)" }}>Injected fault</th>
                      <th className="px-3 py-2 text-left" style={{ color: "var(--text-muted)" }}>True category</th>
                      <th className="px-3 py-2 text-left" style={{ color: "var(--text-muted)" }}>Predicted ranking</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.root_cause.examples.map((ex, i) => (
                      <tr key={i} className="border-t" style={{ borderColor: "var(--border)" }}>
                        <td className="px-3 py-2">{ex.fault_type} ({ex.entity_id})</td>
                        <td className="px-3 py-2">{ex.true_category}</td>
                        <td className="px-3 py-2" style={{ color: ex.predicted_ranking[0] === ex.true_category ? "var(--status-good)" : "var(--status-warning)" }}>
                          {ex.predicted_ranking.join(" > ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
