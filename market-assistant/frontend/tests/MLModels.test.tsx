import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as useMLModelModule from "../src/hooks/useMLModel";
import MLModels from "../src/pages/MLModels";

describe("MLModels page", () => {
  it("shows confidence only alongside its walk-forward baseline comparison, plus the disclaimer", () => {
    vi.spyOn(useMLModelModule, "useMLModel").mockReturnValue({
      data: {
        id: "abc-123",
        instrument_group: "crypto_majors",
        version: "v1",
        published: true,
        fold_metrics: [{ fold: 0, n_train: 100, n_test: 20, accuracy: 0.62 }],
        feature_importances: { ret_1: 12.0, rsi_14: 8.0 },
        model_net_return: 0.15,
        buy_hold_return: 0.06,
        random_return: 0.01,
        threshold: 0.55,
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useMLModelModule.useMLModel>);

    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/ml/abc-123"]}>
          <Routes>
            <Route path="/ml/:id" element={<MLModels />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Confidence must be co-located with an explicit "vs buy-and-hold"
    // comparison, not rendered as a bare number anywhere else on the page.
    const confidenceBlock = screen.getByTestId("confidence-with-baseline");
    expect(confidenceBlock).toHaveTextContent(/confidence/i);
    expect(confidenceBlock).toHaveTextContent(/vs\.? buy-and-hold/i);
    expect(confidenceBlock).toHaveTextContent(/15\.0%/);
    expect(confidenceBlock).toHaveTextContent(/6\.0%/);

    expect(screen.getByText(/fold 0/i)).toBeInTheDocument();
    expect(screen.getByText(/ret_1/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Educational analysis\. Not investment advice\. Past performance ≠ future results\./i,
      ),
    ).toBeInTheDocument();
  });
});
