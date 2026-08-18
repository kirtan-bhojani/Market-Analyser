import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { useCandles } from "../../src/hooks/useCandles";

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
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        candles: [
          { ts: "2024-01-01T00:00:00Z", o: 1, h: 2, l: 0.5, c: 1.5, v: 10 },
          { ts: "2024-01-01T00:01:00Z", o: 1.5, h: 2.5, l: 1, c: 2, v: 12 },
        ],
        delayed: false,
        delay_minutes: 0,
      }),
    }),
  );
});

describe("useCandles", () => {
  it("merges REST history with WS updates without duplicates", async () => {
    const { result } = renderHook(() =>
      useCandles("BTC/USDT", "1m", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
    );

    await waitFor(() => expect(result.current.candles).toHaveLength(2));
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));

    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());

    // update to the already-known last bar (still forming) must replace, not duplicate
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-01-01T00:01:00Z", o: 1.5, h: 3, l: 1, c: 2.8, v: 20 }),
      ),
    );
    expect(result.current.candles).toHaveLength(2);
    expect(result.current.candles[1].c).toBe(2.8);

    // a genuinely new bar must append
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-01-01T00:02:00Z", o: 2.8, h: 3, l: 2.5, c: 2.9, v: 5 }),
      ),
    );
    expect(result.current.candles).toHaveLength(3);
    expect(result.current.candles[2].ts).toBe("2024-01-01T00:02:00Z");
  });

  it("subscribes to the symbol:tf channel once the socket opens", async () => {
    const { result } = renderHook(() =>
      useCandles("BTC/USDT", "1m", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
    );
    await waitFor(() => expect(result.current.candles).toHaveLength(2));
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));

    const socket = FakeWebSocket.instances[0];
    const sendSpy = vi.spyOn(socket, "send");
    act(() => socket.triggerOpen());

    expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ subscribe: "candles:BTC/USDT:1m" }));
  });
});
