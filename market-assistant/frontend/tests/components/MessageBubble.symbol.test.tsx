import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { MessageBubble } from "../../src/components/chat/MessageBubble";

class FakeWebSocket {
  onopen: (() => void) | null = null;
  onmessage: null = null;
  onclose: (() => void) | null = null;
  constructor(public url: string) {}
  send() {}
  close() {}
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ candles: [] }) }),
  );
});

describe("MessageBubble symbol detection", () => {
  it("does not render a mini-chart for indicator text like EMA/VWAP", () => {
    render(
      <MessageBubble
        message={{ role: "assistant", content: "The EMA/VWAP crossover reclaimed support." }}
      />,
    );
    expect(screen.queryByText(/EMA\/VWAP ·/)).not.toBeInTheDocument();
  });

  it("renders a mini-chart for a real trading pair", () => {
    render(
      <MessageBubble
        message={{ role: "assistant", content: "BTC/USDT is testing resistance." }}
      />,
    );
    expect(screen.getByText(/BTC\/USDT ·/)).toBeInTheDocument();
  });
});
