import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { WatchlistTileContainer } from "../../src/components/watchlist/WatchlistTileContainer";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send() {}
  close() {}
  triggerOpen() {
    this.onopen?.();
  }
  triggerMessage(data: string) {
    this.onmessage?.({ data } as MessageEvent<string>);
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
});

describe("WatchlistTileContainer day% baseline", () => {
  it("measures change from the true day open, not the first live candle", async () => {
    // REST returns the day's opening 1d candle (open = 100).
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          candles: [{ ts: "2024-06-15T00:00:00Z", o: 100, h: 130, l: 95, c: 121, v: 1 }],
        }),
      }),
    );

    render(<WatchlistTileContainer symbol="BTC/USDT" />);
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());
    // A mid-day candle: open 110, close 121. Naive baseline would give +10%.
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-06-15T14:00:00Z", o: 110, h: 125, l: 108, c: 121, v: 5 }),
      ),
    );

    // True day open is 100 -> (121-100)/100 = +21.00%.
    await waitFor(() =>
      expect(screen.getByTestId("tile-BTC/USDT-change")).toHaveTextContent("21.00%"),
    );
  });
});
