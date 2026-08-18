import type { MLModelResponse } from "../../hooks/useMLModel";

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/**
 * Horizontal bar comparison of the model's net-of-fees walk-forward return
 * against the buy-and-hold and random baselines. Bars share one scale so the
 * model's edge (or lack of it) is legible at a glance — the model bar carries
 * the accent/up tone only when it clears both baselines.
 */
export function BaselineComparisonChart({ data }: { data: MLModelResponse }) {
  const rows = [
    { key: "model", label: "Model (net of fees)", value: data.model_net_return },
    { key: "buy_hold", label: "Buy & hold", value: data.buy_hold_return },
    { key: "random", label: "Random", value: data.random_return },
  ];
  const beatsBoth =
    data.model_net_return > data.buy_hold_return && data.model_net_return > data.random_return;
  const max = Math.max(0.0001, ...rows.map((r) => Math.abs(r.value)));

  return (
    <div className="ml-bars" data-testid="baseline-comparison-chart">
      {rows.map((r) => (
        <div className="ml-bar-row" key={r.key}>
          <span className="ml-bar-label">{r.label}</span>
          <span className="ml-bar-track">
            <span
              className={`ml-bar-fill ml-bar-${r.key} ${
                r.key === "model" && beatsBoth ? "is-edge" : ""
              }`}
              style={{ width: `${(Math.abs(r.value) / max) * 100}%` }}
            />
          </span>
          <span className="num ml-bar-val">{pct(r.value)}</span>
        </div>
      ))}
    </div>
  );
}
