import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import {
  useDdMonitors,
  useDdLogs,
  useDdMetrics,
  useDdSlos,
  useErrorTrackers,
  useErrorEvents,
  useSynthetics,
  useIncidents,
  useIncident,
  useRcaReports,
  useHealthSummary,
  useSlos,
  useHealthCatalog,
  useHealthStats,
  useHealthForecast,
  useRunbooks,
  useActions,
  useKnowledgeBase,
  useAnalysisResults,
} from "./client";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const fakeJson = <T,>(data: T) => Promise.resolve(new Response(JSON.stringify(data), { status: 200 }));

beforeEach(() => {
  vi.restoreAllMocks();
});

// ─── Monitors ─────────────────────────────────────────

describe("useDdMonitors", () => {
  it("fetches /datadog/monitors with defaults", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdMonitors(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/datadog/monitors");
    expect(url).toContain("page_size=50");
  });

  it("passes name and tags as query params", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdMonitors({ name: "cpu", tags: "env:prod" }), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("name=cpu");
    expect(url).toContain("tags=env%3Aprod");
  });
});

// ─── Logs ─────────────────────────────────────────────

describe("useDdLogs", () => {
  it("does NOT fetch when no filter provided (no match-all default)", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdLogs(), { wrapper: createWrapper() });
    // Give React a tick; the query must stay disabled (enabled requires query or tags)
    await new Promise((r) => setTimeout(r, 50));
    expect(spy).not.toHaveBeenCalled();
  });

  it("fetches when query provided", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdLogs({ query: "service:api" }), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("query=service%3Aapi");
    expect(url).not.toContain("*");
  });

  it("fetches when only tags provided", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdLogs({ tags: "env:prod" }), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("tags=env%3Aprod");
  });
});

// ─── Metrics ──────────────────────────────────────────

describe("useDdMetrics", () => {
  it("fetches /datadog/metrics with params", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useDdMetrics({ metric: "cpu", agg: "avg", tags: "env:prod", days: 7 }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("metric=cpu");
    expect(url).toContain("days=7");
  });

  it("not enabled when metric is empty", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    const { result } = renderHook(() => useDdMetrics(null), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isStale).toBeDefined());
    expect(spy).not.toHaveBeenCalled();
  });
});

// ─── SLOs ─────────────────────────────────────────────

describe("useDdSlos", () => {
  it("fetches with defaults", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useDdSlos(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/datadog/slos");
    expect(url).toContain("limit=50");
  });
});

// ─── Error Tracking ───────────────────────────────────

describe("useErrorTrackers", () => {
  it("fetches /datadog/error-tracking/trackers", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useErrorTrackers(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/datadog/error-tracking/trackers");
    expect(url).toContain("limit=50");
  });
});

describe("useErrorEvents", () => {
  it("POSTs to /datadog/error-tracking/events when query is truthy", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useErrorEvents("service:api"), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const [url, opts] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/datadog/error-tracking/events");
    expect(opts.method).toBe("POST");
    const body = JSON.parse(opts.body as string);
    expect(body.query).toBe("service:api");
  });

  it("not enabled when query is empty", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useErrorEvents(""), { wrapper: createWrapper() });
    expect(spy).not.toHaveBeenCalled();
  });
});

// ─── Synthetics ───────────────────────────────────────

describe("useSynthetics", () => {
  it("fetches /datadog/synthetics", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useSynthetics(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/datadog/synthetics");
  });
});

// ─── Incidents ────────────────────────────────────────

describe("useIncidents", () => {
  it("fetches /incidents with params", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useIncidents({ status: "active", severity: "SEV-1" }), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/incidents");
    expect(url).toContain("status=active");
    expect(url).toContain("severity=SEV-1");
  });

  it("limits to 200", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useIncidents(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("limit=200");
  });
});

describe("useIncident", () => {
  it("fetches /incidents/:id", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useIncident("abc-123"), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/incidents/abc-123");
  });

  it("not enabled when id is empty", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useIncident(""), { wrapper: createWrapper() });
    expect(spy).not.toHaveBeenCalled();
  });
});

// ─── RCA ──────────────────────────────────────────────

describe("useRcaReports", () => {
  it("fetches /rca", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useRcaReports(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/rca");
  });
});

// ─── Health ───────────────────────────────────────────

describe("useHealthSummary", () => {
  it("fetches /health/summary", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useHealthSummary(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/health/summary");
  });
});

describe("useSlos", () => {
  it("fetches /slos without service param", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useSlos(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toBe("/api/v1/slos");
  });

  it("adds service query param", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useSlos("api-gateway"), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("service=api-gateway");
  });
});

describe("useHealthCatalog", () => {
  it("fetches /health/catalog", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useHealthCatalog(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/health/catalog");
  });
});

describe("useHealthStats", () => {
  it("fetches /health/stats", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useHealthStats(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/health/stats");
  });
});

describe("useHealthForecast", () => {
  it("fetches /health/forecast?days=30", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson({}));
    renderHook(() => useHealthForecast(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/health/forecast");
    expect(url).toContain("days=30");
  });
});

// ─── Self‑Healing ─────────────────────────────────────

describe("useRunbooks", () => {
  it("fetches /runbooks", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useRunbooks(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/runbooks");
  });
});

describe("useActions", () => {
  it("fetches /actions with default", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useActions(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/actions");
    expect(url).not.toContain("status=");
  });

  it("sends status filter", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useActions({ status: "pending" }), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("status=pending");
  });
});

// ─── Knowledge Base / Analysis ────────────────────────

describe("useKnowledgeBase", () => {
  it("fetches /kb", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useKnowledgeBase(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/kb");
  });
});

describe("useAnalysisResults", () => {
  it("fetches /analysis", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => fakeJson([]));
    renderHook(() => useAnalysisResults(), { wrapper: createWrapper() });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/analysis");
  });
});
