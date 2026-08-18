import { useState } from "react";

import { CorrelationMatrix } from "../components/analytics/CorrelationMatrix";
import { SeasonalityHeatmap } from "../components/analytics/SeasonalityHeatmap";
import { StrategyComparison } from "../components/analytics/StrategyComparison";
import { Panel } from "../components/common/Panel";
import { useCorrelation } from "../hooks/useCorrelation";
import { useSeasonality } from "../hooks/useSeasonality";
import { useSignals } from "../hooks/useSignals";

const DEFAULT_SYMBOL = "BTC/USDT";
const DEFAULT_INSTRUMENT_ID = 1;

export function Analytics() {
  const [ids, setIds] = useState<string[]>([]);
  const signals = useSignals(DEFAULT_SYMBOL, "1h", DEFAULT_INSTRUMENT_ID);
  const backtestIds = signals
    .map((s) => s.backtest_ref)
    .filter((x): x is string => Boolean(x));
  const corr = useCorrelation("crypto", "1h");
  const seas = useSeasonality(DEFAULT_SYMBOL, "1h", "dow");

  return (
    <div className="analytics-page" data-testid="analytics-page">
      <h1 className="page-title">Analytics</h1>
      <p className="page-sub">Compare strategies · correlations · seasonality</p>

      <Panel title="Strategy comparison" tag="equity curves · net of fees">
        <div className="analytics-toolbar">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setIds(backtestIds.slice(0, 3))}
            disabled={backtestIds.length === 0}
          >
            Load recent strategy backtests
          </button>
        </div>
        <StrategyComparison backtestIds={ids} />
      </Panel>

      <div className="analytics-row">
        <Panel title="Correlation matrix" tag="crypto · 1h returns">
          {corr.isLoading ? (
            <p className="analytics-empty">Loading correlation…</p>
          ) : corr.isError ? (
            <p className="analytics-empty" role="alert">
              Couldn’t load correlation data.
            </p>
          ) : corr.data ? (
            <CorrelationMatrix data={corr.data} />
          ) : (
            <p className="analytics-empty">No correlation data yet.</p>
          )}
        </Panel>

        <Panel title="Seasonality" tag="BTC · day of week">
          {seas.isLoading ? (
            <p className="analytics-empty">Loading seasonality…</p>
          ) : seas.isError ? (
            <p className="analytics-empty" role="alert">
              Couldn’t load seasonality data.
            </p>
          ) : seas.data ? (
            <SeasonalityHeatmap data={seas.data} />
          ) : (
            <p className="analytics-empty">No seasonality data yet.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
