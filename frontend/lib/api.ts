import type {
  Alert, AssistantResponse, Entity, RealWorldReport, Scenario, SiteDetail, SiteOverview, TrainingReport,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  topology: () => request<Entity[]>("/api/topology"),
  overview: () => request<SiteOverview[]>("/api/metrics/overview"),
  siteDetail: (siteId: string, minutes = 60) =>
    request<SiteDetail>(`/api/metrics/site/${siteId}/detail?minutes=${minutes}`),
  series: (entityId: string, metricName: string, minutes = 60) =>
    request(`/api/metrics/${entityId}/${metricName}?minutes=${minutes}`),
  alerts: (resolved?: boolean, limit = 50) =>
    request<Alert[]>(`/api/alerts?limit=${limit}${resolved !== undefined ? `&resolved=${resolved}` : ""}`),
  resolveAlert: (id: number) => request<Alert>(`/api/alerts/${id}/resolve`, { method: "POST" }),
  scenarios: () => request<Scenario[]>("/api/scenarios"),
  startScenario: (fault_type: string, target_entity_id: string) =>
    request<Scenario>("/api/scenarios", { method: "POST", body: JSON.stringify({ fault_type, target_entity_id }) }),
  stopScenario: (id: string) => request<Scenario>(`/api/scenarios/${id}/stop`, { method: "POST" }),
  explainAlert: (alert_id: number) =>
    request<AssistantResponse>("/api/assistant/explain", { method: "POST", body: JSON.stringify({ alert_id }) }),
  evaluation: () => request<TrainingReport>("/api/evaluation"),
  realworld: () => request<RealWorldReport>("/api/realworld"),
};
