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
    vi.fn().mockRejectedValue(new Error("offline")),
  );
});

describe("useLivePrice robustness", () => {
  it("ignores a non-candle frame instead of exposing an undefined last", async () => {
    const { result } = renderHook(() => useLivePrice("BTC/USDT"));
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());

    // A frame with no numeric close (e.g. a signal accidentally on the channel).
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ id: 1, strategy: "orb", ts: "2024-06-15T14:00:00Z" }),
      ),
    );
    // last must stay null (never undefined) so consumers' last.toFixed() is safe.
    expect(result.current.last).toBeNull();

    // A real candle still updates.
    act(() =>
      socket.triggerMessage(
        JSON.stringify({ ts: "2024-06-15T14:01:00Z", o: 100, h: 101, l: 99, c: 105, v: 5 }),
      ),
    );
    expect(result.current.last).toBe(105);
  });
});
