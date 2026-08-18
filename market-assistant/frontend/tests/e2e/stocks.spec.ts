import { expect, test } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

/**
 * Phase 8 journey: a NIFTY-50 equity (RELIANCE.NS) surfaces as a 15-min-delayed
 * feed across the Universe list and the live chart, and the ORB mini-backtest
 * returns honest stats.
 *
 * Mirrors chart.spec.ts / strategies.spec.ts: `fetch` is stubbed via
 * addInitScript so the journey runs against `vite preview` with no backend.
 * The chart's "15-min delayed" badge is driven by the REAL wiring — useCandles
 * reads `delayed`/`delay_minutes` off the /candles envelope and ChartsPage
 * passes them into <CandleChart> — so a delayed envelope here genuinely renders
 * the badge (not a hard-coded string).
 */
async function installFakeBackend(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    const seed = [] as Array<Record<string, number | string>>;
    const base = Date.UTC(2024, 5, 3, 3, 45, 0);
    for (let i = 0; i < 26; i++) {
      const c = 2900 + i;
      seed.push({
        ts: new Date(base + i * 15 * 60_000).toISOString(),
        o: c,
        h: c + 5,
        l: c - 5,
        c: c + 1,
        v: 50_000 + i,
      });
    }

    const origFetch = window.fetch;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/api/instruments")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: 1,
                symbol: "RELIANCE.NS",
                asset_class: "equity",
                exchange: "NSE",
                active: true,
                delayed: true,
                delay_minutes: 15,
              },
            ]),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }

      if (url.includes("/candles")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ candles: seed, delayed: true, delay_minutes: 15 }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
        );
      }

      if (url.includes("/api/strategies/orb/backtest")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              stats: {
                sharpe: 1.1,
                max_dd: 0.12,
                win_rate: 0.55,
                net_return: 0.09,
                trade_count: 12.0,
              },
              n_candles: 26,
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
        const isPost = (init?.method ?? "GET").toUpperCase() === "POST";
        return Promise.resolve(
          new Response(JSON.stringify(isPost ? { id: 1, strategy: "orb" } : []), {
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

    // The chart page layers a WS feed on top of REST history; a no-op fake keeps
    // the page from failing to construct a real socket in preview.
    class FakeWebSocket {
      onopen: (() => void) | null = null;
      onmessage: ((e: MessageEvent<string>) => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public url: string) {
        setTimeout(() => this.onopen?.(), 10);
      }
      send() {}
      close() {
        this.onclose?.();
      }
    }
    // @ts-expect-error override the browser global for the test
    window.WebSocket = FakeWebSocket;
  });
}

test("NIFTY-50 equity shows a 15-min delay badge in Universe and Charts, and ORB backtest returns stats", async ({
  page,
}) => {
  await presetAuth(page);
  await installFakeBackend(page);

  // 1. Universe lists the equity as a 15-min-delayed feed.
  await page.goto("/universe");
  await expect(page.getByText("RELIANCE.NS")).toBeVisible();
  await expect(page.getByText("15-min delayed").first()).toBeVisible();

  // 2. The live chart surfaces the delay badge — proves the REAL envelope
  // wiring (useCandles -> ChartsPage -> CandleChart), not a static label.
  await page.goto("/charts?symbol=RELIANCE.NS&tf=15m");
  await expect(page.getByTestId("candle-chart")).toBeVisible();
  await expect(page.getByText("15-min delayed").first()).toBeVisible();

  // 3. The ORB mini-backtest returns honest, finite stats.
  // NOTE: the real Strategies page has no symbol picker (it is scoped to a
  // single instrument), so the brief's `getByLabel("Symbol").selectOption`
  // does not exist. We assert the REAL control set: run the ORB card's
  // mini-backtest and expect the Net return stat to render. That the ORB
  // backtest runs on EQUITY candles specifically is covered by the backend
  // acceptance test (test_orb_backtest_runs_on_equity_candles).
  await page.goto("/strategies");
  const orbCard = page.locator(".preset-card", { hasText: "Orb" });
  await expect(orbCard).toBeVisible();
  await orbCard.getByRole("button", { name: /run mini-backtest/i }).click();
  await expect(orbCard.getByText(/net return/i)).toBeVisible({ timeout: 15000 });
});
