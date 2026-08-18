/** Read a design token off :root, with a fallback for non-DOM/test contexts. */
export function cssVar(name: string, fallback: string): string {
  if (typeof getComputedStyle === "undefined" || typeof document === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

/** Resolved chart palette derived from the active theme's tokens. */
export function chartPalette() {
  return {
    up: cssVar("--up", "#35d07f"),
    down: cssVar("--down", "#f2606a"),
    volUp: cssVar("--chart-vol-up", "rgba(53,208,127,0.45)"),
    volDown: cssVar("--chart-vol-down", "rgba(242,96,106,0.45)"),
    ema: cssVar("--chart-ema", "#f5a524"),
    vwap: cssVar("--chart-vwap", "#8b7cf6"),
    bb: cssVar("--chart-bb", "#4b7bd6"),
    grid: cssVar("--chart-grid", "rgba(148,163,184,0.08)"),
    text: cssVar("--ink-dim", "#93a2ba"),
    border: cssVar("--line-strong", "rgba(148,163,184,0.22)"),
  };
}
