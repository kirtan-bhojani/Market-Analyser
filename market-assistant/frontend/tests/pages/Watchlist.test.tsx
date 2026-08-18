import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { WatchlistPage } from "../../src/pages/Watchlist";

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

describe("WatchlistPage", () => {
  it("renders a tile with heat color once a candle update arrives", async () => {
    render(<WatchlistPage />);
    expect(screen.getByTestId("tile-BTC/USDT-loading")).toBeInTheDocument();

    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-01-01T00:00:00Z", o: 100, h: 101, l: 99, c: 100, v: 10 }),
      ),
    );
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-01-01T00:01:00Z", o: 100, h: 105, l: 99, c: 103, v: 10 }),
      ),
    );

    await waitFor(() =>
      expect(screen.getByTestId("tile-BTC/USDT-price")).toHaveTextContent("103.00"),
    );
    expect(screen.getByTestId("tile-BTC/USDT-change")).toHaveTextContent("3.00%");
  });
});
