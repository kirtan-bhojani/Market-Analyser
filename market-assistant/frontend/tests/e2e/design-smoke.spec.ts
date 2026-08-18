import { expect, test, type Page } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

const DISCLAIMER_TEXT =
  "Educational analysis. Not investment advice. Past performance ≠ future results.";

// Static pages get pixel-snapshotted. Charts/Watchlist are live (canvas + a
// WebSocket feed) so they are inherently non-deterministic — they are covered
// structurally below and, for Charts, by chart.spec.ts.
const ROUTES: Array<{ path: string; name: string }> = [
  { path: "/", name: "home" },
  { path: "/scanner", name: "scanner" },
  { path: "/strategies", name: "strategies" },
  { path: "/trends", name: "trends" },
  { path: "/analytics", name: "analytics" },
  { path: "/ml", name: "ml" },
  { path: "/chat", name: "chat" },
  { path: "/settings", name: "settings" },
];

const LIVE_ROUTES = ["/charts", "/watchlist"];

const THEMES = ["light", "dark"] as const;

/** Preset the persisted theme so the store rehydrates and stamps data-theme before paint. */
async function presetTheme(page: Page, theme: (typeof THEMES)[number]) {
  await page.addInitScript((t) => {
    window.localStorage.setItem(
      "market-assistant-theme",
      JSON.stringify({ state: { theme: t }, version: 0 })
    );
  }, theme);
}

for (const theme of THEMES) {
  for (const route of ROUTES) {
    test(`${route.name} renders shell + footer (${theme})`, async ({ page }) => {
      await presetAuth(page);
      await presetTheme(page, theme);
      await page.goto(route.path);

      await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
      await expect(page.getByText(DISCLAIMER_TEXT)).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);

      await expect(page).toHaveScreenshot(`${route.name}-${theme}.png`, { fullPage: true });
    });
  }
}

for (const path of LIVE_ROUTES) {
  test(`live page ${path} renders shell + footer`, async ({ page }) => {
    await presetAuth(page);
    await page.goto(path);
    await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    await expect(page.getByText(DISCLAIMER_TEXT)).toBeVisible();
  });
}
