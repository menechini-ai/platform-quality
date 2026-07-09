import { api } from "./client";

const API_BASE = "/api/v1";

export interface AnalyzeResponse {
  incident_id: string;
  analysis: string | null;
  recommendation: string | null;
}

/** Run the full LangGraph pipeline on an incident. */
export function analyzeIncident(incidentId: string, description: string) {
  return api<AnalyzeResponse>("/agents/analyze", {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, description }),
  });
}

/** Stream the LangGraph pipeline execution via SSE. */
export function streamAnalysis(
  incidentId: string,
  description: string,
  onEvent: (node: string, output: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(
        `${API_BASE}/agents/analyze/${incidentId}/stream?description=${encodeURIComponent(description)}`,
        { signal: controller.signal },
      );

      if (!res.ok) {
        onError(new Error(`Stream error: ${res.status}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError(new Error("No response body"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") {
            onDone();
            continue;
          }
          try {
            const event = JSON.parse(payload);
            onEvent(event.node, event.output);
          } catch {
            // skip malformed events
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError(err);
      }
    }
  })();

  return controller;
}
