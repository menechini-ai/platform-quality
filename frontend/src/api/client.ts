import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = "/api/v1";
const TOKEN_KEY = "observai_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(options?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired. Please sign in again.");
  }
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Generic API helper (used by Maturity/Reports pages)
export async function api<T = unknown>(url: string, options?: RequestInit): Promise<T> {
  return fetchJSON<T>(url, options);
}

// ─── Auth ────────────────────────────────────────────────

export interface UserInfo {
  username: string;
  role: string;
}

export async function login(username: string, password: string): Promise<UserInfo> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new Error("Invalid credentials");
  }
  const data = (await res.json()) as { access_token: string };
  setToken(data.access_token);
  return me();
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // ignore network errors during logout
    }
  }
  clearToken();
}

export async function me(): Promise<UserInfo> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    clearToken();
    throw new Error("Not authenticated");
  }
  return res.json() as Promise<UserInfo>;
}

// ─── Monitors ────────────────────────────────────────────

export interface DdMonitor {
  id: number;
  name: string;
  status: string;
  type: string;
  query: string;
  message: string;
  tags: string[];
  overall_state: string;
  created: string;
  updated: string;
}

export function useDdMonitors(filters?: { name?: string; tags?: string; page?: number }) {
  const params = new URLSearchParams();
  if (filters?.name) params.set("name", filters.name);
  if (filters?.tags) params.set("tags", filters.tags);
  if (filters?.page) params.set("page", String(filters.page));
  params.set("page_size", "50");

  return useQuery<DdMonitor[]>({
    queryKey: ["dd-monitors", filters],
    queryFn: () => fetchJSON(`/datadog/monitors?${params}`),
    refetchInterval: 30_000,
  });
}

// ─── Logs ────────────────────────────────────────────────

export interface DdLog {
  id: string;
  content: string;
  service?: string;
  host?: string;
  tags?: string[];
  timestamp: string;
  status?: string;
}

export function useDdLogs(filters?: { query?: string; limit?: number; tags?: string }) {
  const params = new URLSearchParams();
  if (filters?.query) params.set("query", filters.query);
  if (filters?.tags) params.set("tags", filters.tags);
  params.set("limit", String(filters?.limit ?? 50));
  params.set("sort", "-timestamp");

  return useQuery<DdLog[]>({
    queryKey: ["dd-logs", filters],
      queryFn: async () => {
        const res = await fetchJSON<unknown>(`/datadog/logs?${params}`);
        if (Array.isArray(res)) return res as DdLog[];
        return (res as { data?: DdLog[] }).data ?? [];
      },
      enabled: !!(filters?.query || filters?.tags),
    refetchInterval: 30_000,
  });
}

// ─── Metrics ─────────────────────────────────────────────

export interface DdMetricPoint {
  timestamp: number;
  value: number;
}

export interface DdMetricQuery {
  metric: string;
  agg: string;
  tags: string;
  scope?: string;
  days: number;
}

export interface DdMetricResult {
  status: string;
  resp: {
    series?: { metric: string; points: DdMetricPoint[]; tag_set?: string[] }[];
    from_date?: string;
    to_date?: string;
  };
}

export function useDdMetrics(filters: DdMetricQuery | null) {
  const params = new URLSearchParams();

  if (filters) {
    params.set("metric", filters.metric);
    params.set("agg", filters.agg);
    params.set("tags", filters.tags);
    if (filters.scope) params.set("scope", filters.scope);
    params.set("days", String(filters.days));
  }

  return useQuery<DdMetricResult>({
    queryKey: ["dd-metrics", filters],
    queryFn: () => fetchJSON(`/datadog/metrics?${params}`),
    enabled: !!filters?.metric,
  });
}

// ─── SLOs ────────────────────────────────────────────────

export interface DdSlo {
  id: string;
  name: string;
  description?: string;
  target: number;
  tags?: string[];
  type?: string;
  time_window?: string;
  thresholds?: { target: number; timeframe: string }[];
  overall_status?: string;
}

export function useDdSlos(filters?: { query?: string; tags?: string }) {
  const params = new URLSearchParams();
  if (filters?.query) params.set("query", filters.query);
  if (filters?.tags) params.set("tags", filters.tags);
  params.set("limit", "50");

  return useQuery<DdSlo[]>({
    queryKey: ["dd-slos", filters],
    queryFn: () => fetchJSON(`/datadog/slos?${params}`),
    refetchInterval: 60_000,
  });
}

// ─── Error Tracking ─────────────────────────────────────

export interface ErrorTracker {
  id: string;
  attributes?: {
    name?: string;
    status?: string;
    category?: string;
    count?: number;
    last_error?: string;
    first_seen?: string;
    last_seen?: string;
    service?: string;
    env?: string;
  };
}

export function useErrorTrackers(filters?: { limit?: number }) {
  const params = new URLSearchParams();
  params.set("limit", String(filters?.limit ?? 50));

  return useQuery<ErrorTracker[]>({
    queryKey: ["error-trackers", filters],
    queryFn: () => fetchJSON(`/datadog/error-tracking/trackers?${params}`),
    refetchInterval: 60_000,
  });
}

export function useErrorEvents(query: string) {
  return useQuery({
    queryKey: ["error-events", query],
    queryFn: () =>
      fetchJSON("/datadog/error-tracking/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 50, time_range: "1h" }),
      }),
    enabled: !!query,
  });
}

// ─── Synthetics ──────────────────────────────────────────

export interface SyntheticTest {
  public_id: string;
  name: string;
  type: string;
  subtype?: string;
  status: string;
  tags?: string[];
  created_at?: string;
  modified_at?: string;
  locations?: string[];
}

export function useSynthetics(filters?: { limit?: number; tags?: string }) {
  const params = new URLSearchParams();
  params.set("limit", String(filters?.limit ?? 50));
  if (filters?.tags) params.set("tags", filters.tags);

  return useQuery<SyntheticTest[]>({
    queryKey: ["synthetics", filters],
    queryFn: () => fetchJSON(`/datadog/synthetics?${params}`),
    refetchInterval: 60_000,
  });
}

// ─── Incidents ─────────────────────────────────────────

export interface Incident {
  id: string;
  dd_id?: string;
  title: string;
  tags?: string[];
  description?: string;
  severity: string;
  status: string;
  service?: string;
  source?: string;
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
  failure_pattern?: string;
  tags?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.service) params.set("service", filters.service);
  if (filters?.failure_pattern) params.set("failure_pattern", filters.failure_pattern);
  if (filters?.tags) params.set("tags", filters.tags);
  params.set("limit", "200");
  return useQuery<Incident[]>({
    queryKey: ["incidents", filters],
    queryFn: () => fetchJSON(`/incidents?${params}`),
    refetchInterval: 15_000,
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
    refetchInterval: 30_000,
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

// ─── Self-Healing ─────────────────────────────────────

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

export function useApproveAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) =>
      fetchJSON<AutoHealAction>(`/actions/${actionId}/approve`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["actions"] }); },
  });
}

export function useRejectAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) =>
      fetchJSON<AutoHealAction>(`/actions/${actionId}/reject`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["actions"] }); },
  });
}

export function useAnalyzeSelfHealing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tags?: string) => {
      const params = tags ? `?tags=${encodeURIComponent(tags)}` : "";
      return fetchJSON<AnalysisResult>(`/analysis/self-healing${params}`, { method: "POST" });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["analysis"] }); },
  });
}

// ─── Health Catalog / Stats / KB / Analysis ────────────

export interface CatalogItem {
  type: string;
  id: string;
  name: string;
  service?: string;
  severity?: string;
  status?: string;
  failure_pattern?: string;
  tags: string[];
  [key: string]: unknown;
}

export interface HealthStats {
  total_incidents: number;
  active_incidents: number;
  incidents_without_rca: number;
  by_service: Record<string, number>;
  by_failure_pattern: Record<string, number>;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  reports_by_type: Record<string, number>;
  total_runbooks: number;
  heal_actions_by_status: Record<string, number>;
  total_slos: number;
}

export interface KbEntry {
  id: string;
  title: string;
  symptom_pattern?: string;
  root_cause?: string;
  resolution_steps?: string[];
  tags: string[];
  created_at: string;
}

export interface AnalysisResult {
  id: string;
  domain: string;
  action: string;
  title: string;
  summary?: string;
  findings?: Record<string, unknown>;
  recommendations?: string[];
  score?: number;
  severity?: string;
  created_at: string;
}

export function useHealthCatalog(days?: number) {
  const params = days ? `?days=${days}` : "";
  return useQuery<CatalogItem[]>({
    queryKey: ["health-catalog", days],
    queryFn: () => fetchJSON(`/health/catalog${params}`),
    refetchInterval: 30_000,
  });
}

export function useHealthStats(days?: number) {
  const params = days ? `?days=${days}` : "";
  return useQuery<HealthStats>({
    queryKey: ["health-stats", days],
    queryFn: () => fetchJSON(`/health/stats${params}`),
    refetchInterval: 30_000,
  });
}

export function useKnowledgeBase(tag?: string) {
  const params = tag ? `?tag=${tag}` : "";
  return useQuery<KbEntry[]>({
    queryKey: ["kb", tag],
    queryFn: () => fetchJSON(`/kb${params}`),
  });
}

export function useAnalysisResults(domain?: string) {
  const params = domain ? `?domain=${domain}` : "";
  return useQuery<AnalysisResult[]>({
    queryKey: ["analysis", domain],
    queryFn: () => fetchJSON(`/analysis${params}`),
  });
}

export interface ServiceForecast {
  service: string;
  total: number;
  mtbf_hours: number | null;
  next_incident_estimate: string | null;
  by_pattern: Record<string, number>;
  last_incident: string | null;
}

export interface SloBurn {
  name: string;
  service: string | null;
  target: number;
  burn_rate: number | null;
  error_budget_remaining_pct: number | null;
  days_to_exhaustion: number | null;
}

export interface ServiceRisk {
  service: string;
  score: number;
  level: "low" | "medium" | "high";
  reasons: string[];
  mtbf_hours: number | null;
  next_incident_estimate: string | null;
}

export interface HealthForecast {
  window_days: number;
  frequency: ServiceForecast[];
  slo_burn: SloBurn[];
  risk: ServiceRisk[];
  generated_at: string;
}

export function useHealthForecast(days: number = 30) {
  return useQuery<HealthForecast>({
    queryKey: ["health-forecast", days],
    queryFn: () => fetchJSON(`/health/forecast?days=${days}`),
    refetchInterval: 60_000,
  });
}
