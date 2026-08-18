const WIDTH = 80;
const HEIGHT = 24;
const PAD = 2;

/**
 * Tiny inline-SVG sparkline. Scales `points` to fit an 80x24 box and draws a
 * single polyline. Guards against empty / single-point / flat series so the
 * generated path never contains NaN. No external chart dependency.
 */
export function Sparkline({ points }: { points: number[] }) {
  const usableW = WIDTH - PAD * 2;
  const usableH = HEIGHT - PAD * 2;

  let polyline = "";
  if (points.length > 0) {
    const min = Math.min(...points);
    const max = Math.max(...points);
    const span = max - min;
    const stepX = points.length > 1 ? usableW / (points.length - 1) : 0;

    polyline = points
      .map((value, i) => {
        const x = PAD + (points.length > 1 ? i * stepX : usableW / 2);
        // Flat series (span 0) sits on the vertical midline.
        const norm = span > 0 ? (value - min) / span : 0.5;
        const y = PAD + (1 - norm) * usableH;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
  }

  return (
    <svg
      className="sparkline"
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-hidden="true"
    >
      {polyline && (
        <polyline
          points={polyline}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
