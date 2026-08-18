import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useScanHits } from "../../src/hooks/useScanHits";

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

beforeEach(() => {
  captured = null;
  currentToken = "tok-a";
});

const hitFrame = (id: number) =>
  JSON.stringify({
    rule_id: id,
    instrument_id: 1,
    rule_name: "r",
    tf: "5m",
    ts: `t${id}`,
    payload: {},
  });

describe("useScanHits token reset (T2-19)", () => {
  it("clears buffered hits when the token changes (no cross-user bleed)", async () => {
    const { result, rerender } = renderHook(() => useScanHits());
    await waitFor(() => expect(captured).not.toBeNull());

    act(() => captured!(hitFrame(1)));
    expect(result.current.length).toBe(1);

    currentToken = "tok-b";
    act(() => rerender());
    expect(result.current.length).toBe(0);
  });
});
