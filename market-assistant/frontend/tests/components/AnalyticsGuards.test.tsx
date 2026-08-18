import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import { CorrelationMatrix } from "../../src/components/analytics/CorrelationMatrix";
import { SeasonalityHeatmap } from "../../src/components/analytics/SeasonalityHeatmap";

describe("CorrelationMatrix null/ragged safety", () => {
  it("renders a null (non-overlapping) cell without crashing", () => {
    const { getByTestId } = render(
      <CorrelationMatrix
        data={{ symbols: ["A", "B"], matrix: [[1, null], [null, 1]] }}
      />,
    );
    expect(getByTestId("correlation-matrix").textContent).toContain("—");
  });

  it("tolerates a ragged/short matrix row", () => {
    // A row shorter than symbols must not throw on index+map.
    expect(() =>
      render(
        <CorrelationMatrix data={{ symbols: ["A", "B"], matrix: [[1]] }} />,
      ),
    ).not.toThrow();
  });
});

describe("SeasonalityHeatmap ragged safety", () => {
  it("tolerates avg_return/count shorter than labels", () => {
    expect(() =>
      render(
        <SeasonalityHeatmap
          data={{ bucket: "hour", labels: ["00", "01", "02"], avg_return: [0.01], count: [3] }}
        />,
      ),
    ).not.toThrow();
  });
});
