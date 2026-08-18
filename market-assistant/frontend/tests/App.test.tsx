import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/App";
import { createTestRouter } from "../src/router";
import { useAuthStore } from "../src/stores/authStore";

// The live Charts page mounts a chart + WebSocket; keep this smoke test
// deterministic by stubbing the canvas library and network primitives.
vi.mock("lightweight-charts", () => {
  const series = () => ({ setData: vi.fn(), applyOptions: vi.fn() });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: series,
      addHistogramSeries: series,
      addLineSeries: series,
      priceScale: () => ({ applyOptions: vi.fn() }),
      applyOptions: vi.fn(),
      remove: vi.fn(),
    }),
  };
});

class NoopWebSocket {
  onopen: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  onclose: (() => void) | null = null;
  send() {}
  close() {}
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", NoopWebSocket as unknown as typeof WebSocket);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => [] }));
  // These specs assert route-render smoke coverage behind the RequireAuth
  // guard added in Phase 11 — sign in so the guard lets the routes through.
  useAuthStore.setState({
    isAuthenticated: true,
    resolved: true,
    session: { user: { email: "a@b.com" } } as never,
    user: { email: "a@b.com" } as never,
  });
});

const ROUTES: Array<[string, string]> = [
  ["/", "Home"],
  ["/charts", "Charts"],
  ["/scanner", "Scanner"],
  ["/strategies", "Strategies"],
  ["/trends", "Trends"],
  ["/analytics", "Analytics"],
  ["/ml", "ML"],
  ["/chat", "Chat"],
  ["/settings", "Settings"],
];

describe("App", () => {
  it("renders the disclaimer footer", () => {
    render(<App router={createTestRouter("/")} />);

    expect(
      screen.getByText(
        "Educational analysis. Not investment advice. Past performance ≠ future results."
      )
    ).toBeInTheDocument();
  });

  it.each(ROUTES)("mounts the %s page at %s", (path, heading) => {
    render(<App router={createTestRouter(path)} />);

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });
});
