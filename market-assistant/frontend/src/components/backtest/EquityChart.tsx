import { useEffect, useRef } from "react";
import { ColorType, createChart, type UTCTimestamp } from "lightweight-charts";

import type { EquityPoint } from "../../hooks/useBacktest";

/**
 * Renders the backtest equity curve as a lightweight-charts line series.
 */
export function EquityChart({ equityCurve }: { equityCurve: EquityPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "transparent" } },
      height: 300,
    });
    const series = chart.addLineSeries();
    series.setData(
      equityCurve.map((p) => ({
        time: (Date.parse(p.ts) / 1000) as UTCTimestamp,
        value: p.value,
      })),
    );
    return () => chart.remove();
  }, [equityCurve]);

  return <div ref={containerRef} data-testid="equity-chart" />;
}
