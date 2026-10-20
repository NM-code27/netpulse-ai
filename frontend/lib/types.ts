export type EntityType = "site" | "wan_link" | "router" | "switch" | "dns_resolver" | "app_server";

export interface Entity {
  id: string;
  type: EntityType;
  name: string;
  region: string | null;
  tier: string | null;
  parent_id: string | null;
  extra: Record<string, unknown>;
}

export interface SiteOverview {
  id: string;
  name: string;
  region: string | null;
  tier: string | null;
  users: number | null;
  apps: string[] | null;
  latest_value: number | null;
  risk_score: number | null;
  anomaly_score: number | null;
  lead_time_minutes: number | null;
  status: "healthy" | "warning" | "critical" | "no_data";
}

export interface MetricPoint {
  timestamp: string;
  value: number;
}

export interface MetricSeries {
  entity_id: string;
  metric_name: string;
  points: MetricPoint[];
}

export interface RootCauseCandidate {
  category: "wan_link" | "device" | "dns" | "app_tier";
  entity_id: string;
  label: string;
  score: number;
  confidence: number;
}

export interface BusinessImpact {
  sites_affected: string[];
  site_names: string[];
  users_affected: number;
  apps_affected: string[];
  severity_tier: string;
}

export interface Alert {
  id: number;
  created_at: string;
  entity_id: string;
  alert_type: "anomaly" | "predictive_risk";
  severity: "info" | "warning" | "critical";
  metric_name: string | null;
  risk_score: number | null;
  lead_time_minutes: number | null;
  message: string;
  root_cause: { candidates: RootCauseCandidate[]; anomaly_score?: number; breach_probabilities?: Record<string, number> } | null;
  business_impact: BusinessImpact | null;
  scenario_id: string | null;
  resolved: boolean;
}

export interface Scenario {
  id: string;
  name: string;
  fault_type: string;
  target_entity_id: string;
  status: "running" | "completed";
  started_at: string;
  ended_at: string | null;
}

export interface AssistantResponse {
  text: string;
  source: string;
  evidence: Record<string, unknown>;
}

export interface SiteDetail {
  site: { id: string; name: string; region: string | null; tier: string | null; extra: Record<string, unknown> };
  children: { id: string; type: EntityType; name: string }[];
  series: Record<string, Record<string, MetricPoint[]>>;
}

export interface HorizonMetric {
  precision: number;
  recall: number;
  pr_auc: number;
  positive_rate_test: number;
}

export interface MetricReport {
  forecast: { mae: number; rmse: number; horizon_minutes: number };
  risk_classifiers: Record<string, HorizonMetric>;
  false_alarms_per_entity_day: number | null;
  train_rows: number;
  test_rows: number;
}

export interface RootCauseReport {
  evaluated_on: string;
  total_faults_evaluated: number;
  top1_accuracy: number | null;
  top3_accuracy: number | null;
  examples: { fault_type: string; entity_id: string; true_category: string; predicted_ranking: string[] }[];
}

export interface TrainingReport {
  generated_at: string;
  metrics: Record<string, MetricReport>;
  root_cause: RootCauseReport;
}

export interface RealWorldSource {
  available: boolean;
  label: string;
  reason?: string;
  target?: string;
  n_points?: number;
  n_test_points?: number;
  real_mean_rtt_ms?: number;
  real_std_rtt_ms?: number;
  model_mae_ms?: number;
  naive_persistence_mae_ms?: number;
  model_beats_naive?: boolean;
  series?: { timestamp: string; value: number }[];
}

export interface RealWorldReport {
  sources: RealWorldSource[];
}
