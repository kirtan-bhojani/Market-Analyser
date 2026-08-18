import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { MiniChart } from "../../src/components/chat/MiniChart";

class FakeWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(public url: string) {}
  send() {}
  close() {}
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ candles: [], delayed: false, delay_minutes: 0 }),
  });
  vi.stubGlobal("fetch", fetchMock);
});

describe("MiniChart", () => {
  it("does not refetch on every render (stable from/to window)", async () => {
    render(<MiniChart symbol="BTC/USDT" />);
    // Let the effect + any state-driven re-renders settle.
    await new Promise((r) => setTimeout(r, 80));
    // A fresh `new Date()` each render would re-fire the useCandles effect in a
    // loop; a memoized window fetches exactly once.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
