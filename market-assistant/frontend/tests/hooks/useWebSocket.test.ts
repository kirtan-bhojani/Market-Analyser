import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useWebSocket } from "../../src/hooks/useWebSocket";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.onclose?.();
  }
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

describe("useWebSocket", () => {
  it("delivers incoming messages to onMessage", () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket("ws://localhost/ws/candles", { onMessage }));
    const socket = FakeWebSocket.instances[0];

    act(() => socket.triggerOpen());
    act(() => socket.triggerMessage(JSON.stringify({ ts: "x" })));

    expect(onMessage).toHaveBeenCalledWith(JSON.stringify({ ts: "x" }));
  });

  it("reports status transitions and forwards send() as JSON", () => {
    const { result } = renderHook(() =>
      useWebSocket("ws://localhost/ws/candles", { onMessage: vi.fn() }),
    );
    const socket = FakeWebSocket.instances[0];

    expect(result.current.status).toBe("connecting");
    act(() => socket.triggerOpen());
    expect(result.current.status).toBe("open");

    act(() => result.current.send({ subscribe: "candles:BTC/USDT:1m" }));
    expect(socket.sent[0]).toBe(JSON.stringify({ subscribe: "candles:BTC/USDT:1m" }));
  });
});
