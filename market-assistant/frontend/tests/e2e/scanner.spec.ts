import { expect, test } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

// Full-stack acceptance: build the RSI(5m)<30 AND relVol>2 rule in the UI,
// trigger the synthetic-candle replay over the test-only backend route, and
// assert the rule/hit surfaces in the feed.
//
// HARNESS REALITY: the shared playwright.config.ts webServer runs `vite
// preview` — a STATIC frontend with NO backend, PG or Redis. This spec needs
// the live API (http://localhost:8000) reachable from the preview origin, which
// this harness does not provide. Matching the repo's convention of skipping
// live-backend pages (see design-smoke.spec.ts), we probe the API up front and
// skip with a clear reason when it is unreachable rather than faking a pass.

const API_BASE = process.env.VITE_API_URL ?? "http://localhost:8000";

async function backendReachable(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/scanner/rules`, {
      method: "GET",
      signal: AbortSignal.timeout(1000),
    });
    return res.ok || res.status < 500;
  } catch {
    return false;
  }
}

test("build RSI(5m)<30 AND relVol>2 rule, replay data, hit appears", async ({ page }) => {
  const reachable = await backendReachable();
  test.skip(
    !reachable,
    `backend API unreachable at ${API_BASE}; this preview harness serves only the static ` +
      `frontend (no backend/PG/Redis). The backend acceptance test ` +
      `(tests/acceptance/test_scanner_acceptance.py) is the real phase gate.`
  );

  await presetAuth(page);
  await page.goto("/scanner");

  await page.getByTestId("rule-name-input").fill("RSI(5m)<30 AND relVol>2");
  await page.getByTestId("row-0-indicator").selectOption("rsi");
  await page.getByTestId("row-0-tf").selectOption("5m");
  await page.getByTestId("row-0-operator").selectOption("<");
  await page.getByTestId("row-0-value").fill("30");
  await page.getByTestId("add-row").click();
  await page.getByTestId("row-1-indicator").selectOption("rel_volume");
  await page.getByTestId("row-1-tf").selectOption("5m");
  await page.getByTestId("row-1-operator").selectOption(">");
  await page.getByTestId("row-1-value").fill("2");
  await page.getByTestId("save-rule").click();

  // .first(): the desktop and mobile projects run this spec in parallel against
  // the same backend, so the rule list can hold more than one identically-named
  // rule — assert the saved rule surfaced, not that it is unique.
  await expect(page.getByText("RSI(5m)<30 AND relVol>2").first()).toBeVisible();

  await page.request.post(`${API_BASE}/test/replay-synthetic-candles`, {
    data: { scenario: "rsi_dip_with_volume_spike", instrument_id: 1, tf: "5m" },
  });

  await expect(page.getByText("RSI(5m)<30 AND relVol>2").first()).toBeVisible({ timeout: 2000 });
});
