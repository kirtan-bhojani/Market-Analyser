import { describe, expect, it } from "vitest";

import { heatColor } from "../../src/lib/heatColor";

describe("heatColor", () => {
  it("returns strong green above +2%", () => expect(heatColor(0.03)).toBe("#0d5c3a"));
  it("returns weak green between 0 and 2%", () => expect(heatColor(0.01)).toBe("#1f8a5f"));
  it("returns weak red between 0 and -2%", () => expect(heatColor(-0.01)).toBe("#8a2f2f"));
  it("returns strong red below -2%", () => expect(heatColor(-0.03)).toBe("#5c0d0d"));
});
