import { describe, expect, it } from "vitest";

import { heatColor } from "../../src/lib/heatColor";

describe("heatColor NaN handling", () => {
  it("returns a neutral no-data color for NaN input", () => {
    const color = heatColor(NaN);
    // Must not fall through to a red/green bucket (which would paint 'no data'
    // as a strong signal). Neutral grey sentinel.
    expect(color).toBe("#2a2f3a");
  });

  it("still maps real values to heat buckets", () => {
    expect(heatColor(0.03)).toBe("#0d5c3a");
    expect(heatColor(-0.03)).toBe("#5c0d0d");
  });
});
