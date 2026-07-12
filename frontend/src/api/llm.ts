import { api } from "./client";

/** Trigger LLM-powered RCA generation for an incident. */
export function generateRca(incidentId: string) {
  return api<{ llm_rca: string }>(`/rca/${incidentId}/generate`, {
    method: "POST",
  });
}

export interface KbSearchResult {
  id: string;
  title: string;
  symptom_pattern: string | null;
  root_cause: string | null;
  resolution_steps: string[] | null;
  tags: string[] | null;
  score: number;
}

export interface KbSearchResponse {
  results: KbSearchResult[];
  query: string;
  count: number;
}

/** Semantically search the knowledge base. */
export function searchKb(query: string, k = 3) {
  const params = new URLSearchParams({ q: query, k: String(k) });
  return api<KbSearchResponse>(`/kb/search?${params}`);
}
