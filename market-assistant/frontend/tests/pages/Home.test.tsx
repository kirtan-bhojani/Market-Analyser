import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("../../src/hooks/useNews", () => ({ useNews: () => ({ data: [] }) }));
vi.mock("../../src/hooks/useScanHits", () => ({ useScanHits: () => [] }));
vi.mock("../../src/components/home/HomeSignalsPanel", () => ({
  HomeSignalsPanel: () => <div data-testid="home-signals" />,
}));
vi.mock("../../src/components/watchlist/WatchlistTileContainer", () => ({
  WatchlistTileContainer: ({ symbol }: { symbol: string }) => (
    <div data-testid={`wtile-${symbol}`} />
  ),
}));
vi.mock("../../src/components/home/EmbeddedMiniChat", () => ({
  EmbeddedMiniChat: ({ sessionId }: { sessionId: string }) => (
    <div data-testid="emc">{sessionId}</div>
  ),
}));

const createSession = vi.fn().mockResolvedValue({ id: "uuid-1", createdAt: "x" });
vi.mock("../../src/lib/api", async (orig) => ({
  ...(await orig<typeof import("../../src/lib/api")>()),
  createSession: () => createSession(),
}));

import { Home } from "../../src/pages/Home";

describe("Home dashboard (real data, no fabrication)", () => {
  it("contains no fabricated 'live' values", () => {
    render(<Home />);
    expect(screen.queryByText(/14:32:07/)).not.toBeInTheDocument();
    expect(screen.queryByText("67,180")).not.toBeInTheDocument();
    expect(screen.queryByText("312")).not.toBeInTheDocument();
    expect(screen.queryByText(/61% win rate over 240 trades/)).not.toBeInTheDocument();
  });

  it("wires the real panels", async () => {
    render(<Home />);
    expect(screen.getByTestId("home-signals")).toBeInTheDocument();
    expect(screen.getByTestId("wtile-BTC/USDT")).toBeInTheDocument();
    // real scanner-hits empty state (useScanHits -> [])
    expect(screen.getByText(/no hits yet/i)).toBeInTheDocument();
    // real chat session
    await waitFor(() =>
      expect(screen.getByTestId("emc").textContent).toBe("uuid-1"),
    );
  });
});
