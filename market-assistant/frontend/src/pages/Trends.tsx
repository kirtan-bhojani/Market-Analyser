import { EmptyState } from "../components/common/EmptyState";

export function Trends() {
  return (
    <>
      <h1 className="page-title">Trends</h1>
      <p className="page-sub">Market regime · breadth · volatility · sector heat</p>
      <EmptyState
        glyph="↗"
        title="Trend data is warming up"
        message="Regime timelines, breadth gauges, the volatility heatmap, BTC-dominance chart, and equity sector heat appear here once the regime engine ships in Phase 7."
      />
    </>
  );
}
