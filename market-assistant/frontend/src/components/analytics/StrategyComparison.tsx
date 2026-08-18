import { useQueries } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getBacktest } from "../../lib/api";

// Validated categorical order (dataviz light+dark): assigned by entity, never cycled.
const COLORS = ["#2b6cff", "#12855a", "#c8324b", "#a855f7", "#b8860b"];

/** Overlaid equity curves for the selected backtests, aligned on a shared time axis. */
export function StrategyComparison({ backtestIds }: { backtestIds: string[] }) {
  const results = useQueries({
    queries: backtestIds.map((id) => ({
      queryKey: ["backtest", id],
      queryFn: () => getBacktest(id),
    })),
  });

  if (backtestIds.length === 0) {
    return <p className="analytics-empty">Select at least one backtest to compare.</p>;
  }

  const series = backtestIds.map((id, i) => ({
    id,
    label: results[i]?.data?.strategy ?? id,
    curve: results[i]?.data?.equity_curve ?? [],
  }));

  // Merge on timestamp so overlaid lines share one x-axis.
  const byTs: Record<string, Record<string, number | string>> = {};
  for (const s of series) {
    for (const point of s.curve) {
      byTs[point.ts] ??= { ts: point.ts };
      byTs[point.ts][s.id] = point.value;
    }
  }
  const data = Object.values(byTs).sort((a, b) => String(a.ts).localeCompare(String(b.ts)));

  return (
    <div data-testid="strategy-comparison" className="strategy-comparison">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="ts" hide />
          <YAxis width={56} tick={{ fill: "var(--ink-faint)", fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: "var(--panel)",
              border: "1px solid var(--line-strong)",
              borderRadius: 8,
              color: "var(--ink)",
            }}
          />
          <Legend />
          {series.map((s, i) => (
            <Line
              key={s.id}
              type="monotone"
              dataKey={s.id}
              name={s.label}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
