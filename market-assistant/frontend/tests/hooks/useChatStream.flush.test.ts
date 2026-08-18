import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useChatStream } from "../../src/hooks/useChatStream";
import { useChatStore } from "../../src/stores/chatStore";

/** A stream whose final `done` frame is NOT terminated by a blank line. */
function unterminatedStream(frames: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      const body = frames.map((f) => `data: ${JSON.stringify(f)}`).join("\n\n");
      controller.enqueue(encoder.encode(body)); // note: no trailing "\n\n"
      controller.close();
    },
  });
}

beforeEach(() => {
  useChatStore.setState({ sessions: [], activeSessionId: null, messagesBySession: {} });
});

describe("useChatStream trailing flush (T3-18)", () => {
  it("commits a final frame that has no trailing blank line", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: unterminatedStream([
        { type: "token", payload: { text: "BTC up." } },
        { type: "done", payload: { answer: "BTC up." } },
      ]),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useChatStream("session-flush"));
    await act(async () => {
      await result.current.sendMessage("how is BTC?");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    const msgs = result.current.messages;
    expect(msgs[msgs.length - 1]).toEqual({ role: "assistant", content: "BTC up." });
  });
});
