import { useEffect, useState } from "react";

import { Badge } from "../common/Badge";
import type { MiniBacktestResult, StrategyMeta } from "../../hooks/useStrategies";
import { SchemaParamForm } from "./SchemaParamForm";

interface PresetCardProps {
  preset: StrategyMeta;
  onToggle: (enabled: boolean) => void;
  onBacktest: (params: Record<string, number>) => void;
  /** Persisted enabled state for this preset (from the saved config). Drives
   * the toggle so a disabled preset reads Off on reload. Defaults to false. */
  enabled?: boolean;
  /** Honest mini-backtest result to display. Null/undefined = not run yet. */
  result?: MiniBacktestResult | null;
  /** True while this card's mini-backtest request is in flight. */
  pending?: boolean;
  /** Error text if the last mini-backtest failed. */
  error?: string;
}

const REGIME_LABEL: Record<string, string> = {
  trend: "Trend",
  range: "Range",
  any: "Any regime",
};

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/** One value in the honest stats readout. `signed` colors positive green /
 * negative red so a losing preset reads as a loss, never a rosy default. */
function Stat({
  label,
  value,
  signed = 0,
}: {
  label: string;
  value: string;
  signed?: number;
}) {
  const tone = signed > 0 ? "up" : signed < 0 ? "down" : "";
  return (
    <div className="ps-stat">
      <span className="ps-stat-k">{label}</span>
      <span className={`ps-stat-v num ${tone}`}>{value}</span>
    </div>
  );
}

/** A single strategy preset: regime tag, enable toggle, schema-driven param
 * form, mini-backtest trigger, and an honest historical-stats readout. */
export function PresetCard({
  preset,
  onToggle,
  onBacktest,
  enabled: persistedEnabled = false,
  result,
  pending = false,
  error,
}: PresetCardProps) {
  const [enabled, setEnabled] = useState(persistedEnabled);
  const [params, setParams] = useState<Record<string, number>>(preset.default_params);

  // Re-sync when the persisted state arrives/changes (configs load after the
  // first render, and a mutation refetch confirms the flip).
  useEffect(() => setEnabled(persistedEnabled), [persistedEnabled]);

  const stats = result?.stats;

  return (
    <section className="preset-card panel">
      <header className="pc-head">
        <div className="pc-title">
          <h3>{preset.label}</h3>
          <Badge variant={enabled ? "accent" : "neutral"}>
            {REGIME_LABEL[preset.regime_mode] ?? preset.regime_mode}
          </Badge>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label={`Enable ${preset.label}`}
          className={`pc-switch${enabled ? " on" : ""}`}
          onClick={() => {
            const next = !enabled;
            setEnabled(next);
            onToggle(next);
          }}
        >
          <span className="pc-switch-track" aria-hidden="true">
            <span className="pc-switch-thumb" />
          </span>
          <span className="pc-switch-txt">{enabled ? "On" : "Off"}</span>
        </button>
      </header>

      <SchemaParamForm schema={preset.param_schema} values={params} onChange={setParams} />

      <div className="pc-actions">
        <button
          type="button"
          className="pc-run"
          disabled={pending}
          onClick={() => onBacktest(params)}
        >
          {pending ? "Running…" : "Run mini-backtest"}
        </button>
      </div>

      {error && <p className="pc-err">{error}</p>}

      {stats && (
        <div className="pc-stats" data-testid={`stats-${preset.name}`}>
          <div className="pc-stats-grid">
            <Stat label="Win rate" value={pct(stats.win_rate)} />
            <Stat label="Net return" value={pct(stats.net_return)} signed={stats.net_return} />
            <Stat label="Sharpe" value={stats.sharpe.toFixed(2)} signed={stats.sharpe} />
            <Stat label="Max DD" value={pct(stats.max_dd)} signed={stats.max_dd} />
            <Stat label="Trades" value={String(Math.round(stats.trade_count))} />
          </div>
          <p className="pc-stats-note">
            Historical, cost-adjusted over {result?.n_candles ?? 0} candles. Not a forecast.
          </p>
        </div>
      )}
    </section>
  );
}
