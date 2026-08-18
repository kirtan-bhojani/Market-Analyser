import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PresetCard } from "../../src/components/strategies/PresetCard";
import type { StrategyMeta } from "../../src/hooks/useStrategies";

const orbMeta: StrategyMeta = {
  name: "orb",
  label: "Orb",
  regime_mode: "trend",
  param_schema: {
    type: "object",
    properties: {
      or_bars: { type: "integer", minimum: 1, default: 4 },
      rr: { type: "number", minimum: 0.5, default: 2.0 },
    },
    required: ["or_bars", "rr"],
  },
  default_params: { or_bars: 4, rr: 2.0 },
};

describe("PresetCard", () => {
  it("renders a form field for every schema property", () => {
    render(<PresetCard preset={orbMeta} onToggle={vi.fn()} onBacktest={vi.fn()} />);
    expect(screen.getByLabelText(/or_bars/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rr/i)).toBeInTheDocument();
  });

  it("calls onToggle with enabled=true when toggle is switched on", () => {
    const onToggle = vi.fn();
    render(<PresetCard preset={orbMeta} onToggle={onToggle} onBacktest={vi.fn()} />);
    fireEvent.click(screen.getByRole("switch", { name: /enable orb/i }));
    expect(onToggle).toHaveBeenCalledWith(true);
  });

  it("reflects the persisted enabled state and toggles off to false", () => {
    const onToggle = vi.fn();
    render(
      <PresetCard preset={orbMeta} enabled onToggle={onToggle} onBacktest={vi.fn()} />,
    );
    const sw = screen.getByRole("switch", { name: /enable orb/i });
    expect(sw).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("On")).toBeInTheDocument();
    fireEvent.click(sw);
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("calls onBacktest with the current params when the backtest button is clicked", () => {
    const onBacktest = vi.fn();
    render(<PresetCard preset={orbMeta} onToggle={vi.fn()} onBacktest={onBacktest} />);
    fireEvent.click(screen.getByRole("button", { name: /run mini-backtest/i }));
    expect(onBacktest).toHaveBeenCalledWith({ or_bars: 4, rr: 2.0 });
  });
});
