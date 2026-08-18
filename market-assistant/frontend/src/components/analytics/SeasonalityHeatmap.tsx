export interface SeasonalityVM {
  bucket: string;
  labels: string[];
  avg_return: number[];
  count: number[];
}

/** Diverging fill clamped to ±2% mean return; the printed % is the secondary encoding. */
function heatColor(v: number): string {
  const t = Math.max(-0.02, Math.min(0.02, v)) / 0.02;
  const alpha = 0.12 + 0.55 * Math.abs(t);
  return t >= 0 ? `rgba(18, 133, 90, ${alpha})` : `rgba(200, 50, 75, ${alpha})`;
}

export function SeasonalityHeatmap({ data }: { data: SeasonalityVM }) {
  return (
    <div className="seasonality-heatmap" data-testid="seasonality-heatmap">
      {data.labels.map((label, i) => {
        // Guard ragged/short arrays: a label without a paired value reads as 0.
        const ret = data.avg_return[i] ?? 0;
        const n = data.count[i] ?? 0;
        return (
          <div
            key={label}
            className="seasonality-cell"
            title={`${label}: ${(ret * 100).toFixed(2)}% (n=${n})`}
            style={{ background: heatColor(ret) }}
          >
            <span className="seasonality-label">{label}</span>
            <span className="seasonality-value num">{(ret * 100).toFixed(2)}%</span>
          </div>
        );
      })}
    </div>
  );
}
