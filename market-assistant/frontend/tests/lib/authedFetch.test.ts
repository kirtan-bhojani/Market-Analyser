import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/lib/auth", () => ({
  getAccessToken: vi.fn(),
}));

import { getAccessToken } from "../../src/lib/auth";
import { authedFetch, buildWsUrl } from "../../src/lib/api";

const mockedGetAccessToken = vi.mocked(getAccessToken);

describe("authedFetch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }) as unknown as typeof fetch;
  });

  it("attaches Authorization: Bearer <token> when a token exists", async () => {
    mockedGetAccessToken.mockResolvedValue("jwt-123");

    await authedFetch("http://localhost:8000/api/instruments");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/instruments",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer jwt-123" }),
      }),
    );
  });

  it("sends no Authorization header when there is no token", async () => {
    mockedGetAccessToken.mockResolvedValue(null);

    await authedFetch("http://localhost:8000/api/instruments");

    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit & {
      headers: Record<string, string>;
    };
    expect(init?.headers?.Authorization).toBeUndefined();
  });

  it("preserves existing headers like Content-Type", async () => {
    mockedGetAccessToken.mockResolvedValue("jwt-123");

    await authedFetch("http://localhost:8000/api/instruments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });

    const init = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit & {
      headers: Record<string, string>;
    };
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.headers.Authorization).toBe("Bearer jwt-123");
    expect(init.method).toBe("POST");
  });
});

describe("buildWsUrl", () => {
  it("appends ?token=<jwt> when a token is present", () => {
    expect(buildWsUrl("ws://localhost:8000/ws/candles", "jwt-123")).toBe(
      "ws://localhost:8000/ws/candles?token=jwt-123",
    );
  });

  it("returns the base url unchanged when token is null", () => {
    expect(buildWsUrl("ws://localhost:8000/ws/candles", null)).toBe(
      "ws://localhost:8000/ws/candles",
    );
  });
});
