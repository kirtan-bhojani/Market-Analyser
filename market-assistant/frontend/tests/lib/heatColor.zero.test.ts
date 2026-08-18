import { describe, expect, it } from "vitest";

import { heatColor } from "../../src/lib/heatColor";

describe("heatColor at zero", () => {
  it("treats a flat 0% as green (never red under an up arrow)", () => {
    // 0% is shown with an up/flat arrow elsewhere; a red cell contradicts it.
    expect(heatColor(0)).toBe("#1f8a5f");
  });
});
