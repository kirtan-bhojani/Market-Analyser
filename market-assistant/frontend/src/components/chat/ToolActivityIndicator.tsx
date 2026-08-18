import type { ToolEventVM } from "../../stores/chatStore";

const LABELS: Record<string, string> = {
  get_price: "checked price",
  get_candles: "read candles",
  get_indicators: "checked indicators",
  get_regime: "read market regime",
  get_breadth: "checked market breadth",
  get_recent_signals: "read recent signals",
  get_scan_hits: "read scanner hits",
  run_quick_backtest: "ran a quick backtest",
  search_kb: "searched the knowledge base",
  get_news: "checked news",
};

export function ToolActivityIndicator({ event }: { event: ToolEventVM }) {
  return (
    <span className={`tool-activity-chip${event.ok ? "" : " tool-activity-chip--err"}`}>
      <span className="tool-activity-dot" aria-hidden />
      {LABELS[event.name] ?? event.name}
    </span>
  );
}
