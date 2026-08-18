import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { FeatureImportanceChart } from "../../src/components/ml/FeatureImportanceChart";
import type { MLModelResponse } from "../../src/hooks/useMLModel";
import * as useMLModelModule from "../../src/hooks/useMLModel";
import MLModels from "../../src/pages/MLModels";

describe("ML nullable-field guards (T2-21)", () => {
  it("FeatureImportanceChart renders (empty) when feature_importances is null", () => {
    const data = { feature_importances: null } as unknown as MLModelResponse;
    render(<FeatureImportanceChart data={data} />);
    expect(screen.getByTestId("feature-importance-chart")).toBeInTheDocument();
  });

  it("MLModels page does not crash when fold_metrics/feature_importances are null", () => {
    vi.spyOn(useMLModelModule, "useMLModel").mockReturnValue({
      data: {
        id: "abc",
        instrument_group: "crypto_majors",
        version: "v1",
        published: false,
        fold_metrics: null,
        feature_importances: null,
        model_net_return: 0.1,
        buy_hold_return: 0.05,
        random_return: 0.0,
        threshold: 0.55,
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useMLModelModule.useMLModel>);

    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/ml/abc"]}>
          <Routes>
            <Route path="/ml/:id" element={<MLModels />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("fold-metrics-table")).toBeInTheDocument();
    expect(screen.getByTestId("feature-importance-chart")).toBeInTheDocument();
  });
});
