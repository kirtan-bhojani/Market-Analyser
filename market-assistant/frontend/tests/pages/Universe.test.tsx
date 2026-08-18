import type { ReactElement } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../src/lib/api";
import Universe from "../../src/pages/Universe";

vi.spyOn(api, "getInstruments").mockResolvedValue([
  {
    id: 1,
    symbol: "RELIANCE.NS",
    assetClass: "equity",
    exchange: "NSE",
    active: true,
    delayed: true,
    delayMinutes: 15,
  },
]);

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("Universe page", () => {
  it("lists instruments with delay badge", async () => {
    renderWithClient(<Universe />);
    await waitFor(() => expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument());
    expect(screen.getByText("15-min delayed")).toBeInTheDocument();
  });
});
