/**
 * Maps a daily fractional change (e.g. 0.03 = +3%) to a heat-map background.
 * Four buckets: strong/weak green above zero, weak/strong red below.
 */
export function heatColor(changePct: number): string {
  // No-data / undefined change (empty history, non-overlapping window) must not
  // paint as a strong red or green bucket — return a neutral grey sentinel.
  if (Number.isNaN(changePct)) return "#2a2f3a";
  if (changePct > 0.02) return "#0d5c3a";
  if (changePct >= 0) return "#1f8a5f"; // flat 0% is neutral/green, never red
  if (changePct > -0.02) return "#8a2f2f";
  return "#5c0d0d";
}
