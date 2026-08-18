import type { MLModelResponse } from "../../hooks/useMLModel";

/**
 * Ranked horizontal bars of model feature importances, largest first.
 */
export function FeatureImportanceChart({ data }: { data: MLModelResponse }) {
  const rows = Object.entries(data.feature_importances ?? {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(0.0001, ...rows.map(([, v]) => v));

  return (
    <div className="ml-bars" data-testid="feature-importance-chart">
      {rows.map(([name, value]) => (
        <div className="ml-bar-row" key={name}>
          <span className="ml-bar-label num">{name}</span>
          <span className="ml-bar-track">
            <span className="ml-bar-fill ml-bar-feature" style={{ width: `${(value / max) * 100}%` }} />
          </span>
          <span className="num ml-bar-val">{value.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}
