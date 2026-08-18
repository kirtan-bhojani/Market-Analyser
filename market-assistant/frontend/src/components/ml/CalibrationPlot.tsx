import type { FoldMetric } from "../../hooks/useMLModel";

/**
 * Per-fold walk-forward accuracy as a compact column plot. Uses the honest
 * per-fold metrics the API actually returns (no smoothed/aggregate curve),
 * with a 50% reference line so a fold below coin-flip reads immediately.
 */
export function CalibrationPlot({ foldMetrics }: { foldMetrics: FoldMetric[] }) {
  return (
    <div className="ml-folds" data-testid="calibration-plot">
      {foldMetrics.map((f) => (
        <div className="ml-fold-col" key={f.fold}>
          <span className="ml-fold-bar-track">
            <span
              className={`ml-fold-bar-fill ${f.accuracy >= 0.5 ? "is-up" : "is-down"}`}
              style={{ height: `${Math.min(100, f.accuracy * 100)}%` }}
            />
          </span>
          <span className="num ml-fold-acc">{(f.accuracy * 100).toFixed(0)}%</span>
          <span className="ml-fold-label">Fold {f.fold}</span>
        </div>
      ))}
    </div>
  );
}
