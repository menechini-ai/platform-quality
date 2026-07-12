import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AgentPipelinePage } from "./AgentPipelinePage";

describe("AgentPipelinePage", () => {
  it("renders the agent pipeline page", () => {
    render(<AgentPipelinePage />);
    expect(screen.getByText("Agent Pipeline")).toBeDefined();
    expect(screen.getByText("Run Analysis")).toBeDefined();
  });

  it("renders the incident ID input", () => {
    render(<AgentPipelinePage />);
    expect(screen.getByPlaceholderText(/550e8400/)).toBeDefined();
  });

  it("renders the description textarea", () => {
    render(<AgentPipelinePage />);
    expect(screen.getByPlaceholderText("Describe the incident in detail...")).toBeDefined();
  });

  it("renders both action buttons", () => {
    render(<AgentPipelinePage />);
    expect(screen.getByText("Run Full Analysis")).toBeDefined();
    expect(screen.getByText("Stream Analysis")).toBeDefined();
  });
});
