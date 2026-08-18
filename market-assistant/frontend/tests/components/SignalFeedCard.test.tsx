import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SignalFeedCard } from "../../src/components/strategies/SignalFeedCard";
import type { SignalOut } from "../../src/hooks/useSignals";
import type { MiniBacktestStats } from "../../src/hooks/useStrategies";

const signal: SignalOut = {
  id: 1,
  instrument_id: 1,
  strategy: "orb",
  direction: "long",
  ts: "2024-01-01T10:15:00Z",
  confidence: null,
  ref_entry: 107,
  ref_sl: 100,
  ref_tp: 121,
  backtest_ref: "bt-1",
  meta: { or_high: 105, or_low: 100 },
};

// Real backend shape: `trade_count` (serialized as float), win_rate in 0..1.
const backtestStats: MiniBacktestStats = {
  sharpe: 1.1,
  max_dd: -0.05,
  win_rate: 0.58,
  net_return: 0.12,
  trade_count: 42,
};

describe("SignalFeedCard", () => {
  it("renders descriptive recommendation framing, never imperative language", () => {
    render(<SignalFeedCard signal={signal} backtestStats={backtestStats} />);
    expect(screen.getByText(/setup detected/i)).toBeInTheDocument();
    expect(screen.getByText(/58% win rate over 42 trades/i)).toBeInTheDocument();
    expect(screen.getByText(/net of fees/i)).toBeInTheDocument();
    expect(screen.queryByText(/buy now/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/you should/i)).not.toBeInTheDocument();
  });

  it("always renders the disclaimer", () => {
    render(<SignalFeedCard signal={signal} backtestStats={backtestStats} />);
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
  });

  it("omits any performance claim when no backtest stats exist, but keeps the disclaimer", () => {
    render(<SignalFeedCard signal={signal} backtestStats={null} />);
    expect(screen.queryByText(/win rate/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/setup detected/i)).not.toBeInTheDocument();
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
    // Reference levels still shown descriptively.
    expect(screen.getByText(/ref entry/i)).toBeInTheDocument();
  });

  it("shows honest zero/negative stats truthfully", () => {
    render(
      <SignalFeedCard
        signal={signal}
        backtestStats={{ ...backtestStats, win_rate: 0, trade_count: 3 }}
      />,
    );
    expect(screen.getByText(/0% win rate over 3 trades/i)).toBeInTheDocument();
  });
});
