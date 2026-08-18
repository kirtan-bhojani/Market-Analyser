import type { BacktestStats } from "../../hooks/useBacktest";

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/**
 * Labeled grid of headline backtest statistics.
 */
export function StatsGrid({ stats }: { stats: BacktestStats }) {
  return (
    <dl className="stats-grid" data-testid="stats-grid">
      <div>
        <dt>Sharpe</dt>
        <dd className="num">{stats.sharpe.toFixed(2)}</dd>
      </div>
      <div>
        <dt>Max Drawdown</dt>
        <dd className="num">{pct(stats.max_dd)}</dd>
      </div>
      <div>
        <dt>Win Rate</dt>
        <dd className="num">{pct(stats.win_rate)}</dd>
      </div>
      <div>
        <dt>Net Return</dt>
        <dd className="num">{pct(stats.net_return)}</dd>
      </div>
      <div>
        <dt>Trades</dt>
        <dd className="num">{stats.trade_count}</dd>
      </div>
    </dl>
  );
}
