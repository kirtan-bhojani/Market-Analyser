import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useWebSocket reconnect backoff", () => {
  it("backs off exponentially between reconnect attempts", () => {
    renderHook(() => useWebSocket("ws://x/ws", { onMessage: vi.fn() }));
    expect(FakeWebSocket.instances).toHaveLength(1);

    // First close -> reconnect after 1000ms.
    act(() => FakeWebSocket.instances[0].close());
    act(() => void vi.advanceTimersByTime(999));
    expect(FakeWebSocket.instances).toHaveLength(1);
    act(() => void vi.advanceTimersByTime(1));
    expect(FakeWebSocket.instances).toHaveLength(2);

    // Second consecutive close (never opened) -> next delay doubles to 2000ms.
    act(() => FakeWebSocket.instances[1].close());
    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(2); // not yet
    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it("resets the backoff to the base delay after a successful open", () => {
    renderHook(() => useWebSocket("ws://x/ws", { onMessage: vi.fn() }));

    // Escalate the delay: close twice without opening.
    act(() => FakeWebSocket.instances[0].close());
    act(() => void vi.advanceTimersByTime(1000));
    act(() => FakeWebSocket.instances[1].close());
    act(() => void vi.advanceTimersByTime(2000));
    expect(FakeWebSocket.instances).toHaveLength(3);

    // A successful open resets the attempt counter...
    act(() => FakeWebSocket.instances[2].triggerOpen());
    // ...so the next close reconnects after the base 1000ms again.
    act(() => FakeWebSocket.instances[2].close());
    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(4);
  });
});
