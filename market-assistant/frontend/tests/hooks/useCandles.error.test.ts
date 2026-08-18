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
  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send() {}
  close() {}
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
});

describe("useCandles error handling", () => {
  it("keeps an empty series and exposes an error when the REST call fails", async () => {
    // A 401/422/429 returns a JSON error body ({detail: ...}) with no `candles`.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Not authenticated" }),
      }),
    );

    const { result } = renderHook(() =>
      useCandles("BTC/USDT", "1m", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
    );

    await waitFor(() => expect(result.current.error).toBeTruthy());
    // Must never become undefined — Charts reads candles.length.
    expect(Array.isArray(result.current.candles)).toBe(true);
    expect(result.current.candles).toHaveLength(0);
  });
});
