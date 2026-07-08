import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("@/api/client", () => ({
  useIncidents: () => ({ data: [] }),
  useHealthSummary: () => ({ data: [] }),
  useDdMonitors: () => ({ data: [] }),
  useDdSlos: () => ({ data: [] }),
  useDdMetrics: () => ({ data: null }),
}));

import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  it("renders the dashboard title", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders the control room subtitle", () => {
    render(<DashboardPage />);
    expect(screen.getByText(/Control room overview/)).toBeInTheDocument();
  });

  it("renders stat cards", () => {
    render(<DashboardPage />);
    const cards = screen.getAllByText("Active Incidents");
    expect(cards.length).toBeGreaterThanOrEqual(1);
  });
});
