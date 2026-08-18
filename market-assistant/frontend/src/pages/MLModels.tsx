import { useParams } from "react-router-dom";

import { Disclaimer } from "../components/Disclaimer";
import { BaselineComparisonChart } from "../components/ml/BaselineComparisonChart";
import { CalibrationPlot } from "../components/ml/CalibrationPlot";
import { FeatureImportanceChart } from "../components/ml/FeatureImportanceChart";
import { useMLModel } from "../hooks/useMLModel";

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/**
 * ML model detail page. Every reference to model confidence is co-located with
 * its walk-forward, net-of-fees baseline comparison — a calibrated number is
 * never shown as a bare percentage.
 */
export default function MLModels() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useMLModel(id ?? "");

  if (isLoading) return <p className="page-sub">Loading model…</p>;
  if (error || !data) return <p className="page-sub">Failed to load model.</p>;

  return (
    <div className="ml-detail">
      <div className="charts-head">
        <div>
          <h1 className="page-title">
            ML Model · {data.instrument_group} / {data.version}
          </h1>
          <p className="page-sub">
            Purged walk-forward evaluation, isotonic-calibrated confidence, and
            net-of-fees baseline comparison.
          </p>
        </div>
        <span className={`badge ${data.published ? "badge-long" : "badge-neutral"}`}>
          {data.published ? "Published" : "Unpublished"}
        </span>
      </div>

      {/* Signature block: calibrated confidence is ALWAYS paired with its baseline. */}
      <section className="panel">
        <div className="panel-h">
          <h3>Confidence vs baseline</h3>
          <span className="tag">net of fees · threshold {data.threshold}</span>
        </div>
        <div className="panel-b" data-testid="confidence-with-baseline">
          <p className="ml-confidence-lede">
            Calibrated confidence — model walk-forward net return{" "}
            <strong className="num ml-confidence-figure">{pct(data.model_net_return)}</strong>{" "}
            vs buy-and-hold <strong className="num">{pct(data.buy_hold_return)}</strong> and random{" "}
            <strong className="num">{pct(data.random_return)}</strong>.
          </p>
          <BaselineComparisonChart data={data} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-h">
          <h3>Per-fold walk-forward metrics</h3>
        </div>
        <div className="panel-b">
          <table className="universe-table" data-testid="fold-metrics-table">
            <thead>
              <tr>
                <th>Fold</th>
                <th>Train</th>
                <th>Test</th>
                <th>Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {(data.fold_metrics ?? []).map((f) => (
                <tr key={f.fold}>
                  <td className="num">{f.fold}</td>
                  <td className="num">{f.n_train}</td>
                  <td className="num">{f.n_test}</td>
                  <td className="num">{(f.accuracy * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <CalibrationPlot foldMetrics={data.fold_metrics ?? []} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-h">
          <h3>Feature importances</h3>
        </div>
        <div className="panel-b">
          <FeatureImportanceChart data={data} />
        </div>
      </section>

      <Disclaimer />
    </div>
  );
}
