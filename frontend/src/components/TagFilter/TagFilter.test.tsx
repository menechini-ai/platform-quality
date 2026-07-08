import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TagFilter } from "@/components/TagFilter/TagFilter";

describe("TagFilter", () => {
  it("renders input and chip for each tag", () => {
    render(<TagFilter tags={["deploy", "dns"]} onChange={() => {}} />);
    expect(screen.getByPlaceholderText("tags...")).toBeInTheDocument();
    expect(screen.getByText("deploy")).toBeInTheDocument();
    expect(screen.getByText("dns")).toBeInTheDocument();
  });

  it("adds tag on Enter", () => {
    const onChange = vi.fn();
    render(<TagFilter tags={[]} onChange={onChange} />);
    const input = screen.getByPlaceholderText("tags...");
    fireEvent.change(input, { target: { value: "newtag" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["newtag"]);
  });

  it("does not add duplicate tags", () => {
    const onChange = vi.fn();
    render(<TagFilter tags={["existing"]} onChange={onChange} />);
    const input = screen.getByPlaceholderText("tags...");
    fireEvent.change(input, { target: { value: "existing" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not add empty tag", () => {
    const onChange = vi.fn();
    render(<TagFilter tags={[]} onChange={onChange} />);
    const input = screen.getByPlaceholderText("tags...");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes tag when × is clicked", () => {
    const onChange = vi.fn();
    render(<TagFilter tags={["remove-me"]} onChange={onChange} />);
    fireEvent.click(screen.getByText("×"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("renders custom placeholder", () => {
    render(<TagFilter tags={[]} onChange={() => {}} placeholder="filter by tag..." />);
    expect(screen.getByPlaceholderText("filter by tag...")).toBeInTheDocument();
  });
});
