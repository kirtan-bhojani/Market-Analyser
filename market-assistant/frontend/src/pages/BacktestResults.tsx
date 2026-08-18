import { useParams } from "react-router-dom";

import { Disclaimer } from "../components/Disclaimer";
import { EquityChart } from "../components/backtest/EquityChart";
import { StatsGrid } from "../components/backtest/StatsGrid";
import { TradeTable } from "../components/backtest/TradeTable";
import { useBacktest } from "../hooks/useBacktest";

export function BacktestResults() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useBacktest(id ?? "");

  if (isLoading) return <p className="page-sub">Loading backtest…</p>;
  if (error || !data) return <p className="page-sub">Failed to load backtest.</p>;
  if (data.status !== "done" || !data.stats || !data.equity_curve) {
    return <p className="page-sub">Backtest {data.status}…</p>;
  }

  return (
    <div className="backtest-results">
      <div className="charts-head">
        <div>
          <h1 className="page-title">Backtest Results</h1>
          <p className="page-sub">Equity curve, headline stats, and per-point ledger.</p>
        </div>
      </div>

      <section className="panel chart-panel">
        <EquityChart equityCurve={data.equity_curve} />
      </section>

      <StatsGrid stats={data.stats} />
      <TradeTable equityCurve={data.equity_curve} />

      <Disclaimer />
    </div>
  );
}
