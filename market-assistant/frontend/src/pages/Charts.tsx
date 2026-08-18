import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { CandleChart } from "../components/chart/CandleChart";
import { IndicatorOverlays, type OverlayToggles } from "../components/chart/IndicatorOverlays";
import { SymbolSearch } from "../components/chart/SymbolSearch";
import { TimeframeSwitcher } from "../components/chart/TimeframeSwitcher";
import { useCandles } from "../hooks/useCandles";

const DEFAULT_FROM = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
const DEFAULT_TO = new Date().toISOString();
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"];

const STATUS_LABEL: Record<string, string> = {
  open: "Live",
  connecting: "Connecting",
  closed: "Reconnecting",
};

function fmt(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

export function ChartsPage() {
  const [searchParams] = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get("symbol") ?? "BTC/USDT");
  const [tf, setTf] = useState("1m");

  // Follow the global symbol search (AppShell) — it navigates here with a
  // ?symbol= param even when this page is already mounted.
  const symbolParam = searchParams.get("symbol");
  useEffect(() => {
    if (symbolParam) setSymbol(symbolParam);
  }, [symbolParam]);
  const [overlays, setOverlays] = useState<OverlayToggles>({
    ema: true,
    vwap: false,
    bollinger: false,
  });
  const { candles, status, delayed, delayMinutes, error } = useCandles(
    symbol,
    tf,
    DEFAULT_FROM,
    DEFAULT_TO,
  );

  const { last, changePct } = useMemo(() => {
    if (candles.length === 0) return { last: null as number | null, changePct: 0 };
    const first = candles[0].c;
    const lastClose = candles[candles.length - 1].c;
    return { last: lastClose, changePct: first ? (lastClose - first) / first : 0 };
  }, [candles]);

  const dir = changePct > 0 ? "up" : changePct < 0 ? "down" : "";

  return (
    <div className="charts-page">
      <div className="charts-head">
        <div>
          <h1 className="page-title">Charts</h1>
          <p className="page-sub">
            Live candle canvas · crypto real-time · equities 15-min delayed
          </p>
        </div>
        <div className={`live-readout ${dir}`}>
          <span className="live-chip" data-status={status}>
            <span className="live-dot" aria-hidden="true" />
            <span data-testid="ws-status">{STATUS_LABEL[status] ?? status}</span>
          </span>
          <div className="live-px">
            <span className="live-sym">{symbol}</span>
            <span className="live-last num">{last === null ? "—" : fmt(last)}</span>
            {last !== null && (
              <span className={`live-chg num ${dir}`}>
                {changePct >= 0 ? "+" : ""}
                {(changePct * 100).toFixed(2)}%
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="charts-toolbar">
        <SymbolSearch value={symbol} onChange={setSymbol} />
        <TimeframeSwitcher value={tf} onChange={setTf} options={TIMEFRAMES} />
        <IndicatorOverlays value={overlays} onChange={setOverlays} />
      </div>

      <section className="panel chart-panel">
        {error && candles.length === 0 ? (
          <p className="chart-error" data-testid="charts-error" role="alert">
            Couldn’t load candles ({error}). Retrying live…
          </p>
        ) : (
          <CandleChart
            candles={candles}
            overlays={overlays}
            delayed={delayed}
            delayMinutes={delayMinutes}
          />
        )}
      </section>

      <p className="disc chart-disc">
        Educational analysis — overlays are computed indicators, not trade signals.
      </p>
    </div>
  );
}
