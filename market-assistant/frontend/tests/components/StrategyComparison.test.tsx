import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { cloneElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// getBacktest is the data source; return a fixed equity curve per id (no network).
vi.mock("../../src/lib/api", () => ({
  getBacktest: vi.fn(async (id: string) => ({
    id,
    status: "done",
    strategy: id === "bt-1" ? "orb" : "vwap_revert",
    equity_curve: [
      { ts: "2026-01-01T00:00:00Z", value: 10000 },
      { ts: "2026-01-02T00:00:00Z", value: id === "bt-1" ? 10500 : 9800 },
    ],
  })),
}));

// ResponsiveContainer measures the DOM (0×0 in jsdom); give its child fixed dims
// so Recharts actually renders the legend.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children, { width: 480, height: 320 }),
  };
});

import { StrategyComparison } from "../../src/components/analytics/StrategyComparison";

function wrap(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe("StrategyComparison", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders one legend entry per backtest id (one line series each)", async () => {
    render(wrap(<StrategyComparison backtestIds={["bt-1", "bt-2"]} />));
    expect(await screen.findByText(/orb/i)).toBeInTheDocument();
    expect(await screen.findByText(/vwap_revert/i)).toBeInTheDocument();
  });

  it("shows an empty-state when no backtests are selected", () => {
    render(wrap(<StrategyComparison backtestIds={[]} />));
    expect(screen.getByText(/select at least one backtest/i)).toBeInTheDocument();
  });
});
