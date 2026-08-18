import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { BacktestResults } from "../../src/pages/BacktestResults";
import * as useBacktestModule from "../../src/hooks/useBacktest";

vi.mock("lightweight-charts", () => {
  const series = () => ({ setData: vi.fn(), applyOptions: vi.fn() });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addLineSeries: series,
      applyOptions: vi.fn(),
      remove: vi.fn(),
    }),
  };
});

describe("BacktestResults page", () => {
  it("renders stats grid, trade table, and the mandatory disclaimer", () => {
    vi.spyOn(useBacktestModule, "useBacktest").mockReturnValue({
      data: {
        id: "abc-123",
        status: "done",
        stats: {
          sharpe: 1.42,
          max_dd: -0.08,
          win_rate: 0.55,
          net_return: 0.21,
          trade_count: 14,
        },
        equity_curve: [
          { ts: "2024-01-01T00:00:00+00:00", value: 10000 },
          { ts: "2024-01-01T01:00:00+00:00", value: 10050 },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestModule.useBacktest>);

    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/backtests/abc-123"]}>
          <Routes>
            <Route path="/backtests/:id" element={<BacktestResults />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText(/sharpe/i)).toBeInTheDocument();
    expect(screen.getByText(/1\.42/)).toBeInTheDocument();
    expect(screen.getByText(/14/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Educational analysis\. Not investment advice\. Past performance ≠ future results\./,
      ),
    ).toBeInTheDocument();
  });
});
