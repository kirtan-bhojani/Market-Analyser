import { expect, test, type Page } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

const DISCLAIMER = "Educational analysis. Not investment advice. Past performance ≠ future results.";

/**
 * The six core dashboard journeys, driven hermetically against `vite preview`
 * (no backend) — each stubs the `fetch`/`WebSocket`/SSE it needs, mirroring the
 * per-flow specs (chart/strategies/chat). This is the Phase-13 acceptance gate
 * for the end-to-end product experience: watch → visualize → scan → backtest →
 * read recommendation → ask the assistant.
 */

// --- shared fakes ------------------------------------------------------------

async function installChartFeed(page: Page) {
  await page.addInitScript(() => {
    const seed: Array<Record<string, number | string>> = [];
    const base = Date.UTC(2024, 0, 1);
    for (let i = 0; i < 40; i++) {
      const c = 100 + i;
      seed.push({ ts: new Date(base + i * 60_000).toISOString(), o: c, h: c + 1, l: c - 1, c: c + 0.5, v: 10 + i });
    }
    const origFetch = window.fetch;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/candles")) {
        return Promise.resolve(
          new Response(JSON.stringify({ candles: seed, delayed: false, delay_minutes: 0 }), {
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
      private timer: number | undefined;
      private n = 40;
      constructor(public url: string) {
        setTimeout(() => this.onopen?.(), 10);
      }
      send() {
        clearInterval(this.timer);
        this.timer = window.setInterval(() => {
          const c = 100 + this.n;
          this.n += 1;
          this.onmessage?.({
            data: JSON.stringify({ ts: new Date(Date.UTC(2024, 0, 1) + this.n * 60_000).toISOString(), o: c, h: c + 2, l: c - 1, c: c + Math.random(), v: 12 }),
          } as MessageEvent<string>);
        }, 300);
      }
      close() {
        clearInterval(this.timer);
        this.onclose?.();
      }
    }
    // @ts-expect-error override the browser global for the test
    window.WebSocket = FakeWebSocket;
  });
}

async function installStrategiesBackend(page: Page) {
  await page.addInitScript(() => {
    const origFetch = window.fetch;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/strategies/orb/backtest")) {
        return Promise.resolve(
          new Response(JSON.stringify({ stats: { sharpe: 1.2, max_dd: 0.15, win_rate: 0.58, net_return: 0.12, trade_count: 42.0 }, n_candles: 2000 }), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      if (url.includes("/api/strategies")) {
        return Promise.resolve(
          new Response(JSON.stringify([{ name: "orb", label: "Orb", regime_mode: "trend", param_schema: { type: "object", properties: { or_bars: { type: "integer", minimum: 1, default: 4 }, rr: { type: "number", minimum: 0.5, default: 2.0 }, min_rel_volume: { type: "number", minimum: 0, default: 2.0 } }, required: ["or_bars", "rr", "min_rel_volume"] }, default_params: { or_bars: 4, rr: 2.0, min_rel_volume: 2.0 } }]), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      if (url.includes("/api/strategy-configs")) {
        const isPost = (init?.method ?? "GET").toUpperCase() === "POST";
        const config = { id: 1, user_id: "00000000-0000-0000-0000-000000000001", strategy: "orb", instrument_id: 1, tf: "15m", params: { or_bars: 4, rr: 2.0, min_rel_volume: 2.0 }, enabled: true };
        return Promise.resolve(new Response(JSON.stringify(isPost ? config : []), { status: isPost ? 201 : 200, headers: { "content-type": "application/json" } }));
      }
      if (url.includes("/api/signals")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200, headers: { "content-type": "application/json" } }));
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
        setTimeout(() => {
          this.onmessage?.({
            data: JSON.stringify({ id: 1, instrument_id: 1, strategy: "orb", direction: "long", ts: "2024-01-01T10:15:00.000Z", confidence: null, ref_entry: 108, ref_sl: 99, ref_tp: 126, backtest_ref: "bt-1", meta: {} }),
          } as MessageEvent<string>);
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

// --- journeys ----------------------------------------------------------------

test("journey 1 — watch: charts page shows a live price series", async ({ page }) => {
  await presetAuth(page);
  await installChartFeed(page);
  await page.goto("/charts");
  await expect(page.getByTestId("candle-chart")).toBeVisible();
  await expect(page.getByTestId("ws-status")).toHaveText("Live");
});

test("journey 2 — visualize: chart redraws across a timeframe switch", async ({ page }) => {
  await presetAuth(page);
  await installChartFeed(page);
  await page.goto("/charts");
  await page.getByRole("tab", { name: "5m", exact: true }).click();
  await expect(page.getByRole("tab", { name: "5m", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("candle-chart")).toBeVisible();
});

test("journey 3 — scan: build a multi-condition rule in the scanner", async ({ page }) => {
  await presetAuth(page);
  await page.route("**/api/scanner/rules", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto("/scanner");
  await page.getByTestId("rule-name-input").fill("RSI(5m)<30 AND relVol>2");
  await page.getByTestId("row-0-indicator").selectOption("rsi");
  await page.getByTestId("row-0-tf").selectOption("5m");
  await page.getByTestId("row-0-operator").selectOption("<");
  await page.getByTestId("row-0-value").fill("30");
  await page.getByTestId("add-row").click();
  await expect(page.getByTestId("row-1-indicator")).toBeVisible();
});

test("journey 4 — backtest: run a preset mini-backtest and see stats", async ({ page }) => {
  await presetAuth(page);
  await installStrategiesBackend(page);
  await page.goto("/strategies");
  const orbCard = page.locator(".preset-card", { hasText: "Orb" });
  await orbCard.getByRole("switch", { name: /enable orb/i }).click();
  await orbCard.getByRole("button", { name: /run mini-backtest/i }).click();
  await expect(page.locator(".signal-card", { hasText: /orb/i })).toContainText(/win rate over/i, { timeout: 15000 });
});

test("journey 5 — read recommendation: a signal card carries the disclaimer", async ({ page }) => {
  await presetAuth(page);
  await installStrategiesBackend(page);
  await page.goto("/strategies");
  const orbCard = page.locator(".preset-card", { hasText: "Orb" });
  await orbCard.getByRole("switch", { name: /enable orb/i }).click();
  await orbCard.getByRole("button", { name: /run mini-backtest/i }).click();
  await expect(page.locator(".signal-card", { hasText: /orb/i })).toContainText(/not investment advice/i, { timeout: 15000 });
});

test("journey 6 — ask the assistant: grounded, disclaimered reply", async ({ page }) => {
  await presetAuth(page);
  await page.route("**/api/chat/sessions", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "00000000-0000-0000-0000-0000000000aa", user_id: "00000000-0000-0000-0000-000000000001", created_at: "2026-07-11T00:00:00Z" }) });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }
  });
  await page.route("**/api/chat/sessions/*/messages", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/chat/sessions/*/turns", async (route) => {
    const answer = "BTC/USDT on 1h has RSI 58.2 with ADX 24.0, an early uptrend. " + DISCLAIMER;
    const frames = [
      { type: "tool_call", payload: { name: "get_indicators", ok: true } },
      ...answer.split(" ").map((w) => ({ type: "token", payload: { text: w + " " } })),
      { type: "done", payload: { answer } },
    ];
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join("") });
  });
  await page.goto("/chat");
  await page.getByLabel("Message").fill("how is BTC looking on 1h?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/RSI 58\.2/)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(".chat-bubble-disclaimer")).toContainText(/not investment advice/i);
});
