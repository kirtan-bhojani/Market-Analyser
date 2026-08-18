import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const corr = vi.fn();
const seas = vi.fn();
vi.mock("../../src/hooks/useSignals", () => ({ useSignals: () => [] }));
vi.mock("../../src/hooks/useCorrelation", () => ({ useCorrelation: () => corr() }));
vi.mock("../../src/hooks/useSeasonality", () => ({ useSeasonality: () => seas() }));
vi.mock("../../src/components/analytics/StrategyComparison", () => ({
  StrategyComparison: () => <div data-testid="strat-cmp" />,
}));

import { Analytics } from "../../src/pages/Analytics";

describe("Analytics loading/error/empty states", () => {
  it("shows a loading state (not 'no data') while fetching", () => {
    corr.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    seas.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    render(<Analytics />);
    expect(screen.getAllByText(/loading/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/no correlation data yet/i)).not.toBeInTheDocument();
  });

  it("shows an error state distinct from empty", () => {
    corr.mockReturnValue({ isLoading: false, isError: true, data: undefined });
    seas.mockReturnValue({ isLoading: false, isError: false, data: undefined });
    render(<Analytics />);
    expect(screen.getByText(/couldn.t load correlation/i)).toBeInTheDocument();
  });

  it("shows the empty state only when the fetch succeeded with no data", () => {
    corr.mockReturnValue({ isLoading: false, isError: false, data: undefined });
    seas.mockReturnValue({ isLoading: false, isError: false, data: undefined });
    render(<Analytics />);
    expect(screen.getByText(/no correlation data yet/i)).toBeInTheDocument();
  });
});
