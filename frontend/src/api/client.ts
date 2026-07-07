import { useQuery } from "@tanstack/react-query";

const API_BASE = "/api/v1";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ─── Incidents ─────────────────────────────────────────

export interface Incident {
  id: string;
  dd_id?: string;
  title: string;
  description?: string;
  severity: string;
  status: string;
  service?: string;
  started_at: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  timeline: IncidentTimelineEntry[];
}

export interface IncidentTimelineEntry {
  id: string;
  incident_id: string;
  event_type: string;
  content?: string;
  author?: string;
  created_at: string;
}

export function useIncidents(filters?: {
  status?: string;
  severity?: string;
  service?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.service) params.set("service", filters.service);

  return useQuery<Incident[]>({
    queryKey: ["incidents", filters],
    queryFn: () => fetchJSON(`/incidents?${params}`),
  });
}

export function useIncident(id: string) {
  return useQuery<Incident>({
    queryKey: ["incident", id],
    queryFn: () => fetchJSON(`/incidents/${id}`),
    enabled: !!id,
  });
}

// ─── RCA ───────────────────────────────────────────────

export interface RcaReport {
  id: string;
  incident_id: string;
  summary?: string;
  root_cause?: string;
  timeline?: Record<string, unknown>;
  metrics_snapshot?: Record<string, unknown>;
  logs_snapshot?: Record<string, unknown>;
  changes?: Record<string, unknown>;
  recommendations?: string[];
  similar_incidents?: string[];
  created_at: string;
}

export function useRcaReports() {
  return useQuery<RcaReport[]>({
    queryKey: ["rca"],
    queryFn: () => fetchJSON("/rca"),
  });
}

// ─── Health ────────────────────────────────────────────

export interface HealthSummary {
  service: string;
  status: string;
  slis: {
    sli_name: string;
    current_value?: number;
    slo_target?: number;
    burn_rate?: number;
    error_budget_remaining?: number;
  }[];
}

export function useHealthSummary() {
  return useQuery<HealthSummary[]>({
    queryKey: ["health"],
    queryFn: () => fetchJSON("/health/summary"),
  });
}

export interface Slo {
  id: string;
  name: string;
  description?: string;
  target: number;
  time_window: string;
  service?: string;
}

export function useSlos(service?: string) {
  const params = service ? `?service=${service}` : "";
  return useQuery<Slo[]>({
    queryKey: ["slos", service],
    queryFn: () => fetchJSON(`/slos${params}`),
  });
}

// ─── Self-Healing ──────────────────────────────────────

export interface Runbook {
  id: string;
  name: string;
  description?: string;
  triggers?: Record<string, unknown>;
  steps: Record<string, unknown>[];
  is_active: boolean;
  created_at: string;
}

export function useRunbooks() {
  return useQuery<Runbook[]>({
    queryKey: ["runbooks"],
    queryFn: () => fetchJSON("/runbooks"),
  });
}

export interface AutoHealAction {
  id: string;
  incident_id?: string;
  monitor_id?: string;
  action_type: string;
  action_config?: Record<string, unknown>;
  triggered_by: string;
  status: string;
  result?: Record<string, unknown>;
  requested_at: string;
  executed_at?: string;
  completed_at?: string;
}

export function useActions(filters?: { status?: string }) {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);

  return useQuery<AutoHealAction[]>({
    queryKey: ["actions", filters],
    queryFn: () => fetchJSON(`/actions?${params}`),
  });
}
