import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useChatStream } from "../../src/hooks/useChatStream";
import { useChatStore } from "../../src/stores/chatStore";

beforeEach(() => {
  useChatStore.setState({ sessions: [], activeSessionId: null, messagesBySession: {} });
});

describe("useChatStream abort on unmount (T2-18)", () => {
  it("passes an AbortSignal and aborts the in-flight fetch when unmounted", async () => {
    let capturedSignal: AbortSignal | undefined;
    global.fetch = vi.fn().mockImplementation((_url, init: RequestInit) => {
      capturedSignal = init.signal ?? undefined;
      // A body that never closes → the stream stays in-flight until aborted.
      return Promise.resolve({ ok: true, body: new ReadableStream({ start() {} }) });
    }) as unknown as typeof fetch;

    const { result, unmount } = renderHook(() => useChatStream("session-abort"));
    act(() => {
      void result.current.sendMessage("hang please");
    });

    await waitFor(() => expect(capturedSignal).toBeDefined());
    expect(capturedSignal!.aborted).toBe(false);

    act(() => unmount());
    expect(capturedSignal!.aborted).toBe(true);
  });
});
