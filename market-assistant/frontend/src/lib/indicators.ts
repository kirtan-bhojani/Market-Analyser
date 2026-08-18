import type { Candle } from "../hooks/useCandles";

/**
 * Exponential moving average of closes. Matches the backend
 * (`app/scanner/indicators.py`): `NaN` before index `period-1`, seeded with the
 * SMA over the first `period` closes at index `period-1`, then recursive.
 * Returns all `NaN` when fewer than `period` candles are available.
 */
export function ema(candles: Candle[], period: number): number[] {
  const out: number[] = new Array(candles.length).fill(NaN);
  if (candles.length < period) return out;
  const k = 2 / (period + 1);
  let seed = 0;
  for (let i = 0; i < period; i++) seed += candles[i].c;
  seed /= period;
  out[period - 1] = seed;
  let prev = seed;
  for (let i = period; i < candles.length; i++) {
    prev = candles[i].c * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

/** Cumulative volume-weighted average price over typical price (h+l+c)/3. */
export function vwap(candles: Candle[]): number[] {
  let cumPV = 0;
  let cumV = 0;
  return candles.map((c) => {
    const typical = (c.h + c.l + c.c) / 3;
    cumPV += typical * c.v;
    cumV += c.v;
    return cumV === 0 ? typical : cumPV / cumV;
  });
}

export interface BollingerBand {
  upper: number;
  mid: number;
  lower: number;
}

/** Bollinger bands over closes; null until `period` bars are available. */
export function bollinger(
  candles: Candle[],
  period = 20,
  stdDevMultiplier = 2,
): (BollingerBand | null)[] {
  return candles.map((_, i) => {
    if (i < period - 1) return null;
    const window = candles.slice(i - period + 1, i + 1);
    const mean = window.reduce((sum, c) => sum + c.c, 0) / period;
    // Sample standard deviation (ddof=1, divide by period-1) to match the
    // backend (`app/scanner/indicators.py`) and pandas_ta.bbands default.
    const variance = window.reduce((sum, c) => sum + (c.c - mean) ** 2, 0) / (period - 1);
    const stdDev = Math.sqrt(variance);
    return {
      upper: mean + stdDevMultiplier * stdDev,
      mid: mean,
      lower: mean - stdDevMultiplier * stdDev,
    };
  });
}
