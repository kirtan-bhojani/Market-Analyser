import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useSignals } from "../../src/hooks/useSignals";

// Capture the live onMessage handler the hook registers with the socket, plus a
// controllable token so we can drive reset-on-token-change.
let captured: ((data: string) => void) | null = null;
let currentToken: string | null = "tok-a";

vi.mock("../../src/hooks/useWebSocket", () => ({
  useWebSocket: (_url: string, opts: { onMessage: (d: string) => void }) => {
    captured = opts.onMessage;
    return { send: vi.fn(), status: "open" as const };
  },
}));
vi.mock("../../src/hooks/useAccessToken", () => ({
  useAccessToken: () => currentToken,
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  captured = null;
  currentToken = "tok-a";
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] }) as never;
});

const frame = (id: number) =>
  JSON.stringify({ id, instrument_id: 1, strategy: "orb", direction: "long", ts: `t${id}` });

describe("useSignals live buffer (T3-16 cap, T2-19 token reset)", () => {
  it("caps the live buffer at MAX_LIVE (200)", async () => {
    const { result } = renderHook(() => useSignals("BTC/USDT", "1m", 1), { wrapper });
    await waitFor(() => expect(captured).not.toBeNull());

    act(() => {
      for (let i = 0; i < 250; i++) captured!(frame(i));
    });

    expect(result.current.length).toBe(200);
  });

  it("drops the previous user's live signals when the token changes", async () => {
    const { result, rerender } = renderHook(() => useSignals("BTC/USDT", "1m", 1), { wrapper });
    await waitFor(() => expect(captured).not.toBeNull());

    act(() => captured!(frame(1)));
    expect(result.current.length).toBe(1);

    // New user signs in → token flips → buffered signals must clear.
    currentToken = "tok-b";
    act(() => rerender());
    expect(result.current.length).toBe(0);
  });
});
