import { useState } from "react";

import { EmptyState } from "../components/common/EmptyState";
import { PresetCard } from "../components/strategies/PresetCard";
import { SignalFeedCard } from "../components/strategies/SignalFeedCard";
import { useSignals } from "../hooks/useSignals";
import {
  runMiniBacktest,
  useStrategies,
  type MiniBacktestResult,
} from "../hooks/useStrategies";

// Universe picker lands in a later phase; for now the whole page evaluates
// against one instrument/timeframe, surfaced in the header as the active scope.
const DEFAULT_INSTRUMENT_ID = 1;
const DEFAULT_INSTRUMENT_LABEL = "BTC/USDT";
const DEFAULT_TF = "15m";

interface CardState {
  result?: MiniBacktestResult | null;
  pending?: boolean;
  error?: string;
}

export function Strategies() {
  const { strategies, configs, isLoading, isError, upsertStrategyConfig } = useStrategies();
  const [cards, setCards] = useState<Record<string, CardState>>({});
  const signals = useSignals(DEFAULT_INSTRUMENT_LABEL, DEFAULT_TF, DEFAULT_INSTRUMENT_ID);

  // Persisted enabled state for the active scope, keyed by strategy name, so a
  // reload (or an Off toggle) shows each card's true saved state.
  const enabledByStrategy = new Map(
    configs
      .filter((c) => c.instrument_id === DEFAULT_INSTRUMENT_ID && c.tf === DEFAULT_TF)
      .map((c) => [c.strategy, c.enabled]),
  );

  const patch = (name: string, next: CardState) =>
    setCards((prev) => ({ ...prev, [name]: { ...prev[name], ...next } }));

  const handleBacktest = async (name: string, params: Record<string, number>) => {
    patch(name, { pending: true, error: undefined });
    try {
      const result = await runMiniBacktest({
        name,
        instrument_id: DEFAULT_INSTRUMENT_ID,
        tf: DEFAULT_TF,
        params,
      });
      patch(name, { result, pending: false });
    } catch (err) {
      console.error("mini-backtest failed", err);
      patch(name, {
        pending: false,
        error: "Mini-backtest failed. Is the backend running, and is there candle history?",
      });
    }
  };

  return (
    <>
      <div className="strat-head">
        <div>
          <h1 className="page-title">Strategies</h1>
          <p className="page-sub">Preset setups · tune params · run honest mini-backtests</p>
        </div>
        <span className="strat-scope">
          {DEFAULT_INSTRUMENT_LABEL} · {DEFAULT_TF}
        </span>
      </div>

      {isLoading && <p className="page-sub">Loading presets…</p>}

      {isError && (
        <EmptyState
          glyph="⚠"
          title="Couldn't load presets"
          message="The strategies service didn't respond. Check that the backend is running and reload."
        />
      )}

      {!isLoading && !isError && strategies.length === 0 && (
        <EmptyState
          glyph="❏"
          title="No presets available"
          message="No strategy presets are registered yet. Presets appear here once the backend registry is populated."
        />
      )}

      {strategies.length > 0 && (
        <div className="strat-grid">
          {strategies.map((preset) => {
            const state = cards[preset.name] ?? {};
            return (
              <PresetCard
                key={preset.name}
                preset={preset}
                enabled={enabledByStrategy.get(preset.name) ?? false}
                result={state.result}
                pending={state.pending}
                error={state.error}
                onToggle={(enabled) =>
                  upsertStrategyConfig.mutate({
                    strategy: preset.name,
                    instrument_id: DEFAULT_INSTRUMENT_ID,
                    tf: DEFAULT_TF,
                    params: preset.default_params,
                    enabled,
                  })
                }
                onBacktest={(params) => handleBacktest(preset.name, params)}
              />
            );
          })}
        </div>
      )}

      {signals.length > 0 && (
        <section className="signal-feed" aria-label="Signal feed">
          <h2 className="sf-title">Signal feed</h2>
          {signals.map((s) => (
            <SignalFeedCard
              key={s.id}
              signal={s}
              backtestStats={cards[s.strategy]?.result?.stats ?? null}
            />
          ))}
        </section>
      )}
    </>
  );
}
