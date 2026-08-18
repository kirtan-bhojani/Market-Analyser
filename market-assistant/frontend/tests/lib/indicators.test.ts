import { describe, expect, it } from "vitest";

import type { Candle } from "../../src/hooks/useCandles";
import { bollinger, ema, vwap } from "../../src/lib/indicators";

function candle(ts: string, o: number, h: number, l: number, c: number, v: number): Candle {
  return { ts, o, h, l, c, v };
}

describe("ema", () => {
  it("matches backend EMA(3): NaN before period-1, SMA seed at period-1", () => {
    const candles = [10, 11, 12, 13, 14].map((c, i) => candle(`t${i}`, c, c, c, c, 1));
    const result = ema(candles, 3);
    // Backend parity (app/scanner/indicators.py): out[i]=NaN for i<period-1;
    // seed = SMA(first period) = (10+11+12)/3 = 11 at index 2; k = 0.5.
    expect(Number.isNaN(result[0])).toBe(true);
    expect(Number.isNaN(result[1])).toBe(true);
    expect(result[2]).toBeCloseTo(11);
    expect(result[3]).toBeCloseTo(12); // 13*0.5 + 11*0.5
    expect(result[4]).toBeCloseTo(13); // 14*0.5 + 12*0.5
  });

  it("returns all NaN when fewer than `period` candles", () => {
    const candles = [10, 11].map((c, i) => candle(`t${i}`, c, c, c, c, 1));
    const result = ema(candles, 3);
    expect(result.every((v) => Number.isNaN(v))).toBe(true);
    expect(result).toHaveLength(2);
  });
});

describe("vwap", () => {
  it("computes cumulative volume-weighted typical price", () => {
    const candles = [candle("t0", 10, 12, 8, 10, 100), candle("t1", 10, 14, 9, 12, 200)];
    const result = vwap(candles);
    const typical0 = (12 + 8 + 10) / 3;
    const typical1 = (14 + 9 + 12) / 3;
    const expected1 = (typical0 * 100 + typical1 * 200) / 300;
    expect(result[0]).toBeCloseTo(typical0);
    expect(result[1]).toBeCloseTo(expected1);
  });
});

describe("bollinger", () => {
  it("returns null before the period fills, then mean +/- 2 stddev", () => {
    const closes = [10, 10, 10, 10, 20];
    const candles = closes.map((c, i) => candle(`t${i}`, c, c, c, c, 1));
    const result = bollinger(candles, 5, 2);
    expect(result[3]).toBeNull();
    expect(result[4]).not.toBeNull();
    expect(result[4]!.mid).toBeCloseTo(12);
    // Sample stddev (ddof=1): divide by period-1 = 4, matching the backend.
    const variance = ((10 - 12) ** 2 * 4 + (20 - 12) ** 2) / 4;
    const stdDev = Math.sqrt(variance);
    expect(result[4]!.upper).toBeCloseTo(12 + 2 * stdDev);
    expect(result[4]!.lower).toBeCloseTo(12 - 2 * stdDev);
  });
});
