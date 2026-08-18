import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { useLivePrice } from "../../src/hooks/useLivePrice";

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
        candles: [{ ts: "2024-06-15T00:00:00Z", o: 100, h: 130, l: 95, c: 100, v: 1 }],
      }),
    }),
  );
});

describe("useLivePrice", () => {
  it("returns null before data and live last/changePct from the day open", async () => {
    const { result } = renderHook(() => useLivePrice("BTC/USDT"));
    expect(result.current.last).toBeNull();

    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-06-15T14:00:00Z", o: 110, h: 125, l: 108, c: 121, v: 5 }),
      ),
    );

    await waitFor(() => expect(result.current.last).toBe(121));
    expect(result.current.changePct).toBeCloseTo(0.21, 5);
  });
});
