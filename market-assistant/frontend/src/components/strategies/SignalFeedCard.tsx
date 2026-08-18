import { Badge } from "../common/Badge";
import { Disclaimer } from "../Disclaimer";
import type { SignalOut } from "../../hooks/useSignals";
import type { MiniBacktestStats } from "../../hooks/useStrategies";

interface SignalFeedCardProps {
  signal: SignalOut;
  /** Honest per-instrument mini-backtest stats for this signal's strategy.
   * Null = no backtest run yet: show the setup without any performance claim. */
  backtestStats: MiniBacktestStats | null;
}

function fmtLevel(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function fmtTs(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** One detected setup in the signal feed. Framing is strictly descriptive
 * ("setup detected", historical stats) — never a call to action — and every
 * card carries the disclaimer. Stats are the honest mini-backtest numbers;
 * with no stats available, no performance claim is rendered at all. */
export function SignalFeedCard({ signal, backtestStats }: SignalFeedCardProps) {
  const direction = signal.direction === "short" ? "short" : "long";
  const winRatePct = backtestStats ? Math.round(backtestStats.win_rate * 100) : null;
  const tradeCount = backtestStats ? Math.round(backtestStats.trade_count) : null;
  const netReturnPct = backtestStats ? (backtestStats.net_return * 100).toFixed(1) : null;

  const levels: Array<{ k: string; v: number | null }> = [
    { k: "Ref entry", v: signal.ref_entry },
    { k: "Ref stop", v: signal.ref_sl },
    { k: "Ref target", v: signal.ref_tp },
  ];

  return (
    <article className="signal-card" data-direction={direction}>
      <header className="sf-head">
        <span className="sf-strat">{signal.strategy.replace(/_/g, " ")}</span>
        <Badge variant={direction}>{direction === "long" ? "Long setup" : "Short setup"}</Badge>
        <time className="sf-ts num" dateTime={signal.ts}>
          {fmtTs(signal.ts)}
        </time>
      </header>

      <div className="levels">
        {levels.map(({ k, v }) => (
          <div className="lvl" key={k}>
            <div className="k">{k}</div>
            <div className="v num">{v === null ? "—" : fmtLevel(v)}</div>
          </div>
        ))}
      </div>

      {signal.confidence !== null && (
        <p className="sf-conf">
          Model confidence: <span className="num">{Math.round(signal.confidence * 100)}%</span>
        </p>
      )}

      {backtestStats && (
        <p className="sf-framing">
          Setup detected — historically this configuration had {winRatePct}% win rate over{" "}
          {tradeCount} trades ({netReturnPct}% return, net of fees).
        </p>
      )}

      <Disclaimer />
    </article>
  );
}
