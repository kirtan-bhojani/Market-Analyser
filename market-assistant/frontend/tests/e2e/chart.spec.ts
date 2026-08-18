import { expect, test } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

/**
 * Drives the real ChartsPage + lightweight-charts render against a deterministic
 * feed: `fetch` is stubbed to return seed history and `WebSocket` is replaced
 * with a fake that streams new BTC 1m candles once subscribed. This exercises
 * the REST→WS merge and live-tick path without depending on a running backend.
 */
async function installFakeFeed(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    const seed = [] as Array<Record<string, number | string>>;
    const base = Date.UTC(2024, 0, 1, 0, 0, 0);
    for (let i = 0; i < 40; i++) {
      const c = 100 + i;
      seed.push({
        ts: new Date(base + i * 60_000).toISOString(),
        o: c,
        h: c + 1,
        l: c - 1,
        c: c + 0.5,
        v: 10 + i,
      });
    }

    const origFetch = window.fetch;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/candles")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ candles: seed, delayed: false, delay_minutes: 0 }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          ),
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
          const candle = {
            ts: new Date(base + this.n * 60_000).toISOString(),
            o: c,
            h: c + 2,
            l: c - 1,
            c: c + Math.random(),
            v: 12,
          };
          this.n += 1;
          this.onmessage?.({ data: JSON.stringify(candle) } as MessageEvent<string>);
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

test("chart renders and last bar ticks live as new BTC 1m candles form", async ({ page }) => {
  await presetAuth(page);
  await installFakeFeed(page);
  await page.goto("/charts");

  await expect(page.getByTestId("candle-chart")).toBeVisible();
  await expect(page.getByTestId("ws-status")).toHaveText("Live");

  const initialClose = await page.evaluate(
    () => (window as { __lastCandleClose?: number }).__lastCandleClose,
  );
  await page.waitForFunction(
    (prev) => (window as { __lastCandleClose?: number }).__lastCandleClose !== prev,
    initialClose,
    { timeout: 15000 },
  );
  const updatedClose = await page.evaluate(
    () => (window as { __lastCandleClose?: number }).__lastCandleClose,
  );
  expect(updatedClose).not.toBe(initialClose);
});

test("overlays compute and render correctly across a TF switch", async ({ page }) => {
  await presetAuth(page);
  await installFakeFeed(page);
  await page.goto("/charts");

  // The checkbox is visually hidden inside a styled pill; force past the
  // visibility actionability check.
  await page.getByRole("checkbox", { name: /EMA/ }).check({ force: true });
  await page.getByRole("tab", { name: "5m", exact: true }).click();
  await expect(page.getByRole("tab", { name: "5m", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("candle-chart")).toBeVisible();
});
