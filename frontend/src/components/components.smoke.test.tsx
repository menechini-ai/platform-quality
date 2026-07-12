import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { DashboardPage } from "./Dashboard/DashboardPage";
import { IncidentsPage } from "./Incidents/IncidentsPage";
import { IncidentDetailPage } from "./Incidents/IncidentDetailPage";
import { LogsPage } from "./Logs/LogsPage";
import { MetricsPage } from "./Metrics/MetricsPage";
import { MonitorsPage } from "./Monitors/MonitorsPage";
import { SlosPage } from "./Slos/SlosPage";
import { RCAPage } from "./RCA/RCAPage";
import { HealthPage } from "./Health/HealthPage";
import { SelfHealingPage } from "./SelfHealing/SelfHealingPage";
import { MaturityPage } from "./Maturity/MaturityPage";
import { ReportsPage } from "./Reports/ReportsPage";
import { ErrorTrackingPage } from "./ErrorTracking/ErrorTrackingPage";
import { SyntheticsPage } from "./Synthetics/SyntheticsPage";
import { KBSearchPage } from "./KB/KBSearchPage";
import { Layout } from "./Layout/Layout";
import { TagFilter } from "./TagFilter/TagFilter";

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
  );
});

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

function renderPage(Page: () => JSX.Element) {
  return render(<Page />, { wrapper: makeWrapper() });
}

// ─── Smoke tests — page renders without crash ─────────

describe("DashboardPage", () => {
  it("renders heading", () => {
    renderPage(DashboardPage);
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeDefined();
  });
});

describe("IncidentsPage", () => {
  it("renders h1 with Incidents", () => {
    renderPage(IncidentsPage);
    expect(screen.getByRole("heading", { level: 1, name: /incidents/i })).toBeDefined();
  });
});

describe("IncidentDetailPage", () => {
  it("renders loading state", () => {
    render(
      <MemoryRouter initialEntries={["/incidents/fake"]}>
        <Routes>
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
        </Routes>
      </MemoryRouter>,
      { wrapper: ({ children }) => {
        const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
        return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
      }},
    );
    expect(screen.getByText(/loading/i)).toBeDefined();
  });
});

describe("LogsPage", () => {
  it("renders h1 with Logs", () => {
    renderPage(LogsPage);
    expect(screen.getByRole("heading", { level: 1, name: /logs/i })).toBeDefined();
  });
});

describe("MetricsPage", () => {
  it("renders h1 with Metrics", () => {
    renderPage(MetricsPage);
    expect(screen.getByRole("heading", { level: 1, name: /metrics/i })).toBeDefined();
  });
});

describe("MonitorsPage", () => {
  it("renders loading state", () => {
    renderPage(MonitorsPage);
    expect(screen.getByText(/loading/i)).toBeDefined();
  });
});

describe("SlosPage", () => {
  it("renders loading state", () => {
    renderPage(SlosPage);
    expect(screen.getByText(/loading/i)).toBeDefined();
  });
});

describe("RCAPage", () => {
  it("renders loading state", () => {
    renderPage(RCAPage);
    expect(screen.getByText(/loading/i)).toBeDefined();
  });
});

describe("HealthPage", () => {
  it("renders h1", () => {
    renderPage(HealthPage);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
  });
});

describe("SelfHealingPage", () => {
  it("renders h1", () => {
    renderPage(SelfHealingPage);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
  });

  it("renders Run SRE Analysis button", () => {
    renderPage(SelfHealingPage);
    expect(screen.getByRole("button", { name: /run sre analysis/i })).toBeDefined();
  });

  it("renders action status filter tabs", () => {
    renderPage(SelfHealingPage);
    expect(screen.getByText("All")).toBeDefined();
    expect(screen.getByText("Pending")).toBeDefined();
    expect(screen.getByText("Approved")).toBeDefined();
  });
});

describe("MaturityPage", () => {
  it("renders h1", () => {
    renderPage(MaturityPage);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
  });
});

describe("ReportsPage", () => {
  it("renders h1 with Reports", () => {
    renderPage(ReportsPage);
    expect(screen.getByRole("heading", { level: 1, name: /reports/i })).toBeDefined();
  });
});

describe("ErrorTrackingPage", () => {
  it("renders h1 with Error", () => {
    renderPage(ErrorTrackingPage);
    expect(screen.getByRole("heading", { level: 1, name: /error/i })).toBeDefined();
  });
});

describe("SyntheticsPage", () => {
  it("renders loading state", () => {
    renderPage(SyntheticsPage);
    expect(screen.getByText(/loading/i)).toBeDefined();
  });
});

// ─── Layout ───────────────────────────────────────────

describe("Layout", () => {
  it("renders nav with ObservAI title", () => {
    render(<Layout />, { wrapper: ({ children }) => {
      const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      return (
        <QueryClientProvider client={qc}>
          <MemoryRouter>{children}</MemoryRouter>
        </QueryClientProvider>
      );
    }});
    expect(screen.getByText("ObservAI")).toBeDefined();
  });
});

// ─── TagFilter ────────────────────────────────────────

describe("TagFilter", () => {
  it("renders tags input", () => {
    const onChange = vi.fn();
    render(<TagFilter tags={[]} onChange={onChange} />, { wrapper: ({ children }) => {
      const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      return (
        <QueryClientProvider client={qc}>
          <MemoryRouter>{children}</MemoryRouter>
        </QueryClientProvider>
      );
    }});
    expect(screen.getByPlaceholderText(/tags/i)).toBeDefined();
  });
});

describe("KBSearchPage", () => {
  it("renders heading and search input", () => {
    renderPage(KBSearchPage);
    expect(screen.getByRole("heading", { level: 1, name: /knowledge base/i })).toBeDefined();
    expect(screen.getByPlaceholderText(/search.*knowledge/i)).toBeDefined();
  });
});
