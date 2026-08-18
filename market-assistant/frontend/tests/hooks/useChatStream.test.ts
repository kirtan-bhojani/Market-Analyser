import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useChatStream } from "../../src/hooks/useChatStream";
import { useChatStore } from "../../src/stores/chatStore";

function sseStream(frames: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
      }
      controller.close();
    },
  });
}

beforeEach(() => {
  useChatStore.setState({ sessions: [], activeSessionId: null, messagesBySession: {} });
});

describe("useChatStream", () => {
  it("accumulates streamed tokens into the final assistant message", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([
        { type: "token", payload: { text: "BTC " } },
        { type: "token", payload: { text: "is up." } },
        { type: "done", payload: { answer: "BTC is up." } },
      ]),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useChatStream("session-1"));
    await act(async () => {
      await result.current.sendMessage("how is BTC?");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    const msgs = result.current.messages;
    expect(msgs[msgs.length - 1]).toEqual({ role: "assistant", content: "BTC is up." });
  });

  it("records tool_call events into toolEvents", async () => {
    const events: object[] = [];
    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        body: sseStream([
          { type: "tool_call", payload: { name: "get_indicators", ok: true } },
          { type: "done", payload: { answer: "done" } },
        ]),
      });
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useChatStream("session-1"));
    let captured: typeof result.current.toolEvents = [];
    await act(async () => {
      const p = result.current.sendMessage("how is BTC?");
      await p;
    });
    captured = result.current.toolEvents;
    expect(captured).toHaveLength(1);
    expect(captured[0].name).toBe("get_indicators");
    void events;
  });
});
