import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import { useChatStream } from "../../src/hooks/useChatStream";

function sseStream(frames: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useChatStream malformed SSE frame", () => {
  it("skips a bad data line and still commits the turn's answer", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: sseStream([
          "data: {not valid json\n\n",
          'data: {"type":"token","payload":{"text":"hi"}}\n\n',
          'data: {"type":"done","payload":{"answer":"hello there"}}\n\n',
        ]),
      }),
    );

    const { result } = renderHook(() => useChatStream("s1"));
    await act(async () => {
      await result.current.sendMessage("hey");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    // A single malformed frame must NOT abort the turn.
    expect(result.current.error).toBeNull();
    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("hello there");
  });
});
