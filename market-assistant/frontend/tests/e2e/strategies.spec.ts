import { expect, test } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

/**
 * Drives the real Strategies page against a deterministic fake backend:
 * `fetch` is stubbed to serve the ORB preset, echo the strategy-config
 * enable call, and return honest-looking mini-backtest stats; `WebSocket` is
 * replaced with a fake that pushes one ORB signal after the page subscribes.
 * Mirrors chart.spec.ts's fetch/WebSocket-stub pattern — Playwright's
 * webServer here is `vite preview` only, with no backend underneath it.
 */
async function installFakeBackend(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    const origFetch = window.fetch;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/api/strategies/orb/backtest")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              stats: {
                sharpe: 1.2,
                max_dd: 0.15,
                win_rate: 0.58,
                net_return: 0.12,
                trade_count: 42.0,
              },
              n_candles: 2000,
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }

      if (url.includes("/api/strategies")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                name: "orb",
                label: "Orb",
                regime_mode: "trend",
                param_schema: {
                  type: "object",
                  properties: {
                    or_bars: { type: "integer", minimum: 1, default: 4 },
                    rr: { type: "number", minimum: 0.5, default: 2.0 },
                    min_rel_volume: { type: "number", minimum: 0, default: 2.0 },
                  },
                  required: ["or_bars", "rr", "min_rel_volume"],
                },
                default_params: { or_bars: 4, rr: 2.0, min_rel_volume: 2.0 },
              },
            ]),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }

      if (url.includes("/api/strategy-configs")) {
        const config = {
          id: 1,
          user_id: "00000000-0000-0000-0000-000000000001",
          strategy: "orb",
          instrument_id: 1,
          tf: "15m",
          params: { or_bars: 4, rr: 2.0, min_rel_volume: 2.0 },
          enabled: true,
        };
        // GET lists configs (array); POST upserts one (object echo). The page
        // reads the list to reflect each card's persisted enabled state, so the
        // GET must return an array or `configs.filter(...)` throws.
        const isPost = (init?.method ?? "GET").toUpperCase() === "POST";
        return Promise.resolve(
          new Response(JSON.stringify(isPost ? config : []), {
            status: isPost ? 201 : 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }

      if (url.includes("/api/signals")) {
        return Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }

      return origFetch(input, init);
    }) as typeof window.fetch;

    class FakeWebSocket {
      onopen: (() => void) | null = null;
      onmessage: ((e: MessageEvent<string>) => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public url: string) {
        setTimeout(() => this.onopen?.(), 10);
      }
      send() {
        // Delay past the mini-backtest stub's (near-instant) resolution so
        // the signal card's honest win-rate framing has backtestStats to
        // read when the live signal arrives.
        setTimeout(() => {
          const signal = {
            id: 1,
            instrument_id: 1,
            strategy: "orb",
            direction: "long",
            ts: "2024-01-01T10:15:00.000Z",
            confidence: null,
            ref_entry: 108,
            ref_sl: 99,
            ref_tp: 126,
            backtest_ref: "bt-1",
            meta: {},
          };
          this.onmessage?.({ data: JSON.stringify(signal) } as MessageEvent<string>);
        }, 300);
      }
      close() {
        this.onclose?.();
      }
    }
    // @ts-expect-error override the browser global for the test
    window.WebSocket = FakeWebSocket;
  });
}

test("enable ORB on BTC 15m and see a recommendation card with stats", async ({ page }) => {
  await presetAuth(page);
  await installFakeBackend(page);
  await page.goto("/strategies");

  const orbCard = page.locator(".preset-card", { hasText: "Orb" });
  await orbCard.getByRole("switch", { name: /enable orb/i }).click();
  await orbCard.getByRole("button", { name: /run mini-backtest/i }).click();

  const feedCard = page.locator(".signal-card", { hasText: /orb/i });
  await expect(feedCard).toBeVisible({ timeout: 15000 });
  await expect(feedCard).toContainText(/setup detected/i);
  await expect(feedCard).toContainText(/win rate over/i);
  await expect(feedCard).toContainText(/not investment advice/i);
});
