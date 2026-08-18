import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const getInstruments = vi.fn();
const getSignals = vi.fn();
vi.mock("../../src/lib/api", () => ({
  getInstruments: () => getInstruments(),
  getSignals: (id: number) => getSignals(id),
}));

import { HomeSignalsPanel } from "../../src/components/home/HomeSignalsPanel";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const inst = (id: number, symbol: string) => ({
  id,
  symbol,
  assetClass: "crypto",
  exchange: "binance",
  active: true,
  delayed: false,
  delayMinutes: 0,
});

const sig = (id: number) => ({
  id,
  instrument_id: 1,
  strategy: "orb",
  direction: "long",
  ts: "2026-01-01T00:00:00Z",
  confidence: 0.7,
  ref_entry: 100,
  ref_sl: 95,
  ref_tp: 110,
  backtest_ref: null,
  meta: null,
});

describe("HomeSignalsPanel", () => {
  it("renders real signals for watchlist instruments", async () => {
    getInstruments.mockResolvedValue([inst(1, "BTC/USDT")]);
    getSignals.mockResolvedValue([sig(1)]);
    wrap(<HomeSignalsPanel />);
    await waitFor(() => expect(screen.getByText("Long setup")).toBeInTheDocument());
  });

  it("shows an empty state when there are no signals (no fabricated setups)", async () => {
    getInstruments.mockResolvedValue([inst(1, "BTC/USDT")]);
    getSignals.mockResolvedValue([]);
    wrap(<HomeSignalsPanel />);
    await waitFor(() => expect(screen.getByText(/no active signals/i)).toBeInTheDocument());
  });
});
