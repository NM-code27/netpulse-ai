"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { FlaskConical, Square } from "lucide-react";
import { api } from "@/lib/api";
import type { Entity } from "@/lib/types";

const FAULT_TYPES_BY_ENTITY_TYPE: Record<string, { value: string; label: string }[]> = {
  wan_link: [
    { value: "link_degradation", label: "WAN link degradation" },
    { value: "bandwidth_saturation", label: "Bandwidth saturation" },
  ],
  router: [{ value: "device_down", label: "Device failure" }],
  switch: [{ value: "device_down", label: "Device failure" }],
  dns_resolver: [{ value: "dns_failure", label: "DNS resolver failure" }],
  app_server: [{ value: "app_latency", label: "Application tier latency spike" }],
};

const FAULT_CAPABLE_TYPES = Object.keys(FAULT_TYPES_BY_ENTITY_TYPE);

export function ScenarioControls() {
  const { data: topology } = useSWR("topology", api.topology);
  const { data: scenarios, mutate: refetchScenarios } = useSWR("scenarios", api.scenarios, {
    refreshInterval: 5000,
  });

  const targets = useMemo(
    () => (topology || []).filter((e: Entity) => FAULT_CAPABLE_TYPES.includes(e.type)),
    [topology]
  );

  // No selection has been made yet until the user picks one -- the actual
  // dropdown values fall back to the first option below. Deriving the
  // defaults at render time (rather than syncing them via useEffect) avoids
  // an extra render pass and a stale-state window on every topology/target change.
  const [chosenTargetId, setChosenTargetId] = useState<string>("");
  const [chosenFaultType, setChosenFaultType] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const targetId = targets.some((t: Entity) => t.id === chosenTargetId) ? chosenTargetId : (targets[0]?.id ?? "");
  const selectedEntity = targets.find((t: Entity) => t.id === targetId);
  const availableFaults = selectedEntity ? FAULT_TYPES_BY_ENTITY_TYPE[selectedEntity.type] || [] : [];
  const faultType = availableFaults.some((f) => f.value === chosenFaultType)
    ? chosenFaultType
    : (availableFaults[0]?.value ?? "");

  const running = (scenarios || []).filter((s) => s.status === "running");

  async function inject() {
    if (!targetId || !faultType) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.startScenario(faultType, targetId);
      refetchScenarios();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start scenario");
    } finally {
      setSubmitting(false);
    }
  }

  async function stop(id: string) {
    await api.stopScenario(id);
    refetchScenarios();
  }

  return (
    <div
      className="relative overflow-hidden rounded-2xl border p-5"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div
        className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full opacity-50"
        style={{ background: "var(--accent-soft)" }}
      />
      <div className="relative mb-3 flex items-center gap-2.5">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-xl"
          style={{ background: "var(--accent-soft)" }}
        >
          <FlaskConical size={16} color="var(--accent)" />
        </div>
        <h3 className="text-sm font-bold">Inject a fault scenario</h3>
      </div>
      <p className="relative mb-4 text-xs" style={{ color: "var(--text-muted)" }}>
        Trigger a controlled fault on the live simulator and watch the risk score, forecast,
        and root-cause assistant respond in real time.
      </p>

      <div className="relative flex flex-col gap-2">
        <select
          value={targetId}
          onChange={(e) => { setChosenTargetId(e.target.value); setChosenFaultType(""); }}
          className="w-full rounded-lg border px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--accent)]"
          style={{ background: "var(--surface-sunken)", borderColor: "var(--border)" }}
        >
          {targets.map((t: Entity) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.type})
            </option>
          ))}
        </select>

        <select
          value={faultType}
          onChange={(e) => setChosenFaultType(e.target.value)}
          className="w-full rounded-lg border px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--accent)]"
          style={{ background: "var(--surface-sunken)", borderColor: "var(--border)" }}
        >
          {availableFaults.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>

        <button
          onClick={inject}
          disabled={submitting || !targetId}
          className="w-full rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-transform active:scale-95 disabled:opacity-50"
          style={{ background: "var(--accent-gradient)", boxShadow: "0 4px 14px -4px rgba(42,110,224,0.5)" }}
        >
          {submitting ? "Starting..." : "Inject fault"}
        </button>
      </div>

      {error && <p className="relative mt-2 text-xs" style={{ color: "var(--status-critical)" }}>{error}</p>}

      {running.length > 0 && (
        <div className="relative mt-4 space-y-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Active scenarios
          </div>
          {running.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded-lg border px-3 py-2 text-xs"
              style={{ borderColor: "var(--border)", background: "var(--surface-sunken)" }}
            >
              <span className="flex items-center gap-2">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: "var(--status-critical)", animation: "pulse-ring 1.6s infinite" }}
                />
                {s.name}
              </span>
              <button
                onClick={() => stop(s.id)}
                className="flex items-center gap-1 rounded-md px-2 py-1 font-medium transition-colors hover:bg-[var(--status-critical-soft)]"
                style={{ color: "var(--status-critical)" }}
              >
                <Square size={12} /> Stop
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
