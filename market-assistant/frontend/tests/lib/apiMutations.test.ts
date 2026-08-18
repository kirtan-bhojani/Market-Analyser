import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

import {
  createInstrument,
  createSession,
  getInstruments,
  listSessions,
  seedNifty50,
  updateInstrument,
} from "../../src/lib/api";

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 500,
    json: async () => ({ detail: "boom" }),
  }) as unknown as typeof fetch;
});

describe("api mutations surface HTTP errors", () => {
  it("createSession rejects on a non-ok response", async () => {
    await expect(createSession()).rejects.toThrow();
  });
  it("createInstrument rejects on a non-ok response", async () => {
    await expect(
      createInstrument({ symbol: "BTC/USDT", assetClass: "crypto", exchange: "binance" }),
    ).rejects.toThrow();
  });
  it("updateInstrument rejects on a non-ok response", async () => {
    await expect(updateInstrument(1, true)).rejects.toThrow();
  });
  it("seedNifty50 rejects on a non-ok response", async () => {
    await expect(seedNifty50()).rejects.toThrow();
  });
  it("getInstruments rejects on a non-ok response", async () => {
    await expect(getInstruments()).rejects.toThrow();
  });
  it("listSessions rejects on a non-ok response", async () => {
    await expect(listSessions()).rejects.toThrow();
  });
});
