import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { useCandles } from "../../src/hooks/useCandles";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  closed = false;
  constructor(public url: string) {
    // Real browsers reject a WebSocket URL with a fragment identifier — mirror
    // that so we never regress into folding state into the URL fragment.
    if (url.includes("#")) {
      throw new SyntaxError("Fragment identifiers are not allowed in WebSocket URLs.");
    }
    FakeWebSocket.instances.push(this);
  }
  send() {}
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ candles: [] }) }),
  );
});

describe("useCandles symbol switch", () => {
  it("tears down the old socket and opens a fresh one when the symbol changes", async () => {
    const { rerender } = renderHook(
      ({ sym }: { sym: string }) =>
        useCandles(sym, "1m", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
      { initialProps: { sym: "BTC/USDT" } },
    );

    await waitFor(() => expect(FakeWebSocket.instances.length).toBe(1));
    const first = FakeWebSocket.instances[0];

    rerender({ sym: "ETH/USDT" });

    // A symbol change must open a NEW socket (fresh server subscription) and
    // close the old one, so stale frames from the previous channel can't leak.
    await waitFor(() => expect(FakeWebSocket.instances.length).toBe(2));
    expect(first.closed).toBe(true);
  });
});
