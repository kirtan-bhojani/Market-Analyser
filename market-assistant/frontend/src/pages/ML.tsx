import { EmptyState } from "../components/common/EmptyState";

export function ML() {
  return (
    <>
      <h1 className="page-title">ML</h1>
      <p className="page-sub">Walk-forward metrics · calibration · feature importances · baselines</p>
      <EmptyState
        glyph="◈"
        title="No model published"
        message="Per-fold walk-forward metrics, calibration plots, feature importances, and model-vs-baseline comparisons appear here once a model is trained and published. The ML service ships in Phase 9."
      />
    </>
  );
}
