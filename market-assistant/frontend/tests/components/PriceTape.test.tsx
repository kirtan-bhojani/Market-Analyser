import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { PriceTape } from "../../src/components/layout/PriceTape";

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

describe("PriceTape", () => {
  it("shows placeholders (never fabricated prices) before data", () => {
    render(<PriceTape />);
    expect(screen.queryByText("67,412")).not.toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("renders a live price once a candle arrives", async () => {
    render(<PriceTape />);
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThan(0));
    act(() => FakeWebSocket.instances[0].triggerOpen());
    act(() =>
      FakeWebSocket.instances[0].triggerMessage(
        JSON.stringify({ ts: "2024-06-15T14:00:00Z", o: 110, h: 125, l: 108, c: 121, v: 5 }),
      ),
    );
    await waitFor(() => expect(screen.getByText("121.00")).toBeInTheDocument());
  });
});
