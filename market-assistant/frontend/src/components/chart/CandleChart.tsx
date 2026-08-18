import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import type { Candle } from "../../hooks/useCandles";
import { bollinger, ema, vwap } from "../../lib/indicators";
import { chartPalette } from "../../lib/chartTheme";
import { useThemeStore } from "../../stores/themeStore";
import { DelayBadge } from "../common/DelayBadge";
import type { OverlayToggles } from "./IndicatorOverlays";

export interface CandleChartProps {
  candles: Candle[];
  overlays: OverlayToggles;
  delayed?: boolean;
  delayMinutes?: number;
}

const barTime = (ts: string) =>
  Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp;

export function CandleChart({ candles, overlays, delayed, delayMinutes }: CandleChartProps) {
  const theme = useThemeStore((s) => s.theme);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbUpperRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbLowerRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Create the chart + series once. Guarded so headless environments without
  // canvas/ResizeObserver (jsdom unit tests) render the container and no-op.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    // jsdom (unit tests) has no real 2D canvas; skip the chart lib entirely so
    // the container still renders. Real browsers return a context and proceed.
    if (typeof document !== "undefined") {
      const probe = document.createElement("canvas");
      if (!probe.getContext || !probe.getContext("2d")) return;
    }
    let chart: IChartApi;
    try {
      chart = createChart(el, {
        autoSize: typeof ResizeObserver !== "undefined",
        width: el.clientWidth || 800,
        height: 460,
        layout: { background: { type: ColorType.Solid, color: "transparent" } },
        timeScale: { timeVisible: true, secondsVisible: false },
      });
    } catch {
      return;
    }
    chartRef.current = chart;
    candleSeriesRef.current = chart.addCandlestickSeries();
    volumeSeriesRef.current = chart.addHistogramSeries({
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    emaSeriesRef.current = chart.addLineSeries({ lineWidth: 2, priceLineVisible: false });
    vwapSeriesRef.current = chart.addLineSeries({ lineWidth: 2, priceLineVisible: false });
    bbUpperRef.current = chart.addLineSeries({ lineWidth: 1, priceLineVisible: false });
    bbLowerRef.current = chart.addLineSeries({ lineWidth: 1, priceLineVisible: false });

    return () => chart.remove();
  }, []);

  // Re-skin whenever the theme flips.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const p = chartPalette();
    chart.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: p.text,
      },
      grid: {
        vertLines: { color: p.grid },
        horzLines: { color: p.grid },
      },
      rightPriceScale: { borderColor: p.border },
      timeScale: { borderColor: p.border },
    });
    candleSeriesRef.current?.applyOptions({
      upColor: p.up,
      downColor: p.down,
      wickUpColor: p.up,
      wickDownColor: p.down,
      borderVisible: false,
    });
    emaSeriesRef.current?.applyOptions({ color: p.ema });
    vwapSeriesRef.current?.applyOptions({ color: p.vwap });
    bbUpperRef.current?.applyOptions({ color: p.bb });
    bbLowerRef.current?.applyOptions({ color: p.bb });
  }, [theme]);

  // Push data + overlays.
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;
    const p = chartPalette();

    candleSeriesRef.current.setData(
      candles.map((c) => ({
        time: barTime(c.ts),
        open: c.o,
        high: c.h,
        low: c.l,
        close: c.c,
      })),
    );
    volumeSeriesRef.current.setData(
      candles.map((c) => ({
        time: barTime(c.ts),
        value: c.v,
        color: c.c >= c.o ? p.volUp : p.volDown,
      })),
    );

    if (overlays.ema && emaSeriesRef.current) {
      const values = ema(candles, 21);
      // ema() now emits NaN during the warm-up window; lightweight-charts
      // rejects NaN values, so drop those points before setData.
      emaSeriesRef.current.setData(
        candles
          .map((c, i) => ({ time: barTime(c.ts), value: values[i] }))
          .filter((pt) => Number.isFinite(pt.value)),
      );
    } else {
      emaSeriesRef.current?.setData([]);
    }

    if (overlays.vwap && vwapSeriesRef.current) {
      const values = vwap(candles);
      vwapSeriesRef.current.setData(
        candles.map((c, i) => ({ time: barTime(c.ts), value: values[i] })),
      );
    } else {
      vwapSeriesRef.current?.setData([]);
    }

    if (overlays.bollinger && bbUpperRef.current && bbLowerRef.current) {
      const bands = bollinger(candles, 20, 2);
      const toPoints = (pick: (b: NonNullable<(typeof bands)[number]>) => number) =>
        candles
          .map((c, i) => (bands[i] ? { time: barTime(c.ts), value: pick(bands[i]!) } : null))
          .filter((pt): pt is { time: UTCTimestamp; value: number } => pt !== null);
      bbUpperRef.current.setData(toPoints((b) => b.upper));
      bbLowerRef.current.setData(toPoints((b) => b.lower));
    } else {
      bbUpperRef.current?.setData([]);
      bbLowerRef.current?.setData([]);
    }

    (window as unknown as { __lastCandleClose?: number }).__lastCandleClose =
      candles.at(-1)?.c;
  }, [candles, overlays]);

  return (
    <div className="candle-chart-wrap">
      <div className="candle-chart-head">
        <DelayBadge delayed={delayed ?? false} delayMinutes={delayMinutes ?? 0} />
      </div>
      <div ref={containerRef} data-testid="candle-chart" className="candle-chart" />
    </div>
  );
}
