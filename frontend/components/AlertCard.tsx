"use client";

import { useState } from "react";
import { Bot, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";
import type { Alert, AssistantResponse } from "@/lib/types";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--status-critical)",
  warning: "var(--status-warning)",
  info: "var(--text-muted)",
};

export function AlertCard({ alert, onResolved }: { alert: Alert; onResolved?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [assistant, setAssistant] = useState<AssistantResponse | null>(null);
  const [loadingAssistant, setLoadingAssistant] = useState(false);

  const candidates = alert.root_cause?.candidates ?? [];
  const impact = alert.business_impact;

  async function askAssistant() {
    setLoadingAssistant(true);
    try {
      const res = await api.explainAlert(alert.id);
      setAssistant(res);
    } catch {
      setAssistant({ text: "Could not reach the assistant service.", source: "error", evidence: {} });
    } finally {
      setLoadingAssistant(false);
    }
  }

  return (
    <div
      className="overflow-hidden rounded-2xl border transition-shadow hover:shadow-md"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div className="flex items-stretch gap-0">
        <span className="w-1 shrink-0" style={{ background: SEVERITY_COLOR[alert.severity] }} />
        <div className="flex flex-1 items-start justify-between gap-3 p-4">
          <div className="flex items-start gap-2.5">
            <div>
              <p className="text-sm font-medium leading-snug">{alert.message}</p>
              <p className="mt-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
                {new Date(alert.created_at).toLocaleString()} &middot; {alert.alert_type.replace("_", " ")}
                {alert.risk_score !== null && ` · risk ${alert.risk_score}/100`}
              </p>
            </div>
          </div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="shrink-0 rounded-md p-1 transition-colors hover:bg-[var(--surface-sunken)]"
            style={{ color: "var(--text-muted)" }}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="space-y-3 border-t px-4 pb-4 pt-3" style={{ borderColor: "var(--border)" }}>
          {candidates.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                Root-cause ranking
              </div>
              <div className="space-y-1">
                {candidates.slice(0, 3).map((c) => (
                  <div key={c.category} className="flex items-center justify-between text-xs">
                    <span style={{ color: "var(--text-secondary)" }}>{c.label}</span>
                    <span className="tabular" style={{ color: "var(--text-muted)" }}>{c.confidence}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {impact && (
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
              Impact: {impact.users_affected} users across {impact.sites_affected.length} site(s)
              {impact.apps_affected.length > 0 && ` -- ${impact.apps_affected.join(", ")}`}
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={askAssistant}
              disabled={loadingAssistant}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
              style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              <Bot size={13} />
              {loadingAssistant ? "Thinking..." : "Ask assistant"}
            </button>
            {!alert.resolved && onResolved && (
              <button
                onClick={async () => { await api.resolveAlert(alert.id); onResolved(); }}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium"
                style={{ color: "var(--text-muted)" }}
              >
                <CheckCircle2 size={13} /> Mark resolved
              </button>
            )}
          </div>

          {assistant && (
            <div
              className="rounded-lg border p-3 text-xs leading-relaxed whitespace-pre-wrap"
              style={{ background: "var(--surface-sunken)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
            >
              {assistant.text}
              <div className="mt-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                source: {assistant.source}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
