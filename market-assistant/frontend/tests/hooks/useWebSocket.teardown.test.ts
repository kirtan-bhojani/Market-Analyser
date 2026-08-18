import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useWebSocket } from "../../src/hooks/useWebSocket";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send() {}
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

describe("useWebSocket teardown (T2-20)", () => {
  it("detaches handlers before close: no message delivery / no reconnect after unmount", () => {
    const onMessage = vi.fn();
    const { unmount } = renderHook(() =>
      useWebSocket("ws://localhost/ws/candles", { onMessage }),
    );
    const socket = FakeWebSocket.instances[0];
    act(() => socket.triggerOpen());

    act(() => unmount());

    // The socket the effect cleanup closed must no longer fan messages out, and
    // its close must not schedule a reconnect (a new FakeWebSocket instance).
    socket.triggerMessage(JSON.stringify({ ts: "late" }));
    expect(onMessage).not.toHaveBeenCalled();
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(socket.onclose).toBeNull();
  });
});
