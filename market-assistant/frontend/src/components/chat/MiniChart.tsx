import { useMemo } from "react";

import { CandleChart } from "../chart/CandleChart";
import { useCandles } from "../../hooks/useCandles";

const NO_OVERLAYS = { ema: false, vwap: false, bollinger: false };

/** Compact price snapshot for a symbol referenced in a chat answer. Reuses the
 * Phase-3 lightweight-charts wrapper; overlays off to keep it glanceable. */
export function MiniChart({ symbol, tf = "1h" }: { symbol: string; tf?: string }) {
  // Memoize the window: a fresh `new Date()` each render produces new ISO
  // strings, which are useCandles deps — that re-fires its effect (setCandles
  // -> re-render -> new dates) in an infinite fetch loop.
  const { from, to } = useMemo(() => {
    const now = new Date();
    const start = new Date(now.getTime() - 1000 * 60 * 60 * 24 * 5);
    return { from: start.toISOString(), to: now.toISOString() };
  }, []);
  const { candles, delayed, delayMinutes } = useCandles(symbol, tf, from, to);

  return (
    <figure className="mini-chart">
      <figcaption className="mini-chart-cap">
        {symbol} · {tf}
      </figcaption>
      <div className="mini-chart-canvas">
        <CandleChart
          candles={candles}
          overlays={NO_OVERLAYS}
          delayed={delayed}
          delayMinutes={delayMinutes}
        />
      </div>
    </figure>
  );
}
