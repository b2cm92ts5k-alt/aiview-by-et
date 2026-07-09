import { TIMEFRAMES } from "@aiview/shared-types";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TimeframeSelector from "./TimeframeSelector";

describe("TimeframeSelector", () => {
  it("renders all 11 timeframes (F3)", () => {
    render(<TimeframeSelector value="15m" onChange={() => {}} />);
    expect(TIMEFRAMES).toHaveLength(11);
    for (const tf of TIMEFRAMES) {
      expect(screen.getByRole("button", { name: tf })).toBeInTheDocument();
    }
  });

  it("fires onChange with the clicked tf", () => {
    const onChange = vi.fn();
    render(<TimeframeSelector value="15m" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "4h" }));
    expect(onChange).toHaveBeenCalledWith("4h");
  });
});
