import { expect, test } from "@playwright/test";

import { presetAuth } from "./_auth-helper";

const DISCLAIMER = "Educational analysis. Not investment advice. Past performance ≠ future results.";

// The preview server serves the built frontend only (no backend), so the chat
// API is mocked deterministically: a session, empty history, and a canned SSE
// turn that reports a tool call then streams a grounded, disclaimered answer.
test("ask a question and see tool activity + a disclaimered answer", async ({ page }) => {
  await presetAuth(page);
  await page.route("**/api/chat/sessions", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "00000000-0000-0000-0000-0000000000aa",
          user_id: "00000000-0000-0000-0000-000000000001",
          created_at: "2026-07-11T00:00:00Z",
        }),
      });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }
  });

  await page.route("**/api/chat/sessions/*/messages", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );

  await page.route("**/api/chat/sessions/*/turns", async (route) => {
    const answer =
      "BTC/USDT on 1h has RSI 58.2 with ADX 24.0, an early uptrend. " + DISCLAIMER;
    const frames = [
      { type: "tool_call", payload: { name: "get_indicators", ok: true } },
      ...answer.split(" ").map((w) => ({ type: "token", payload: { text: w + " " } })),
      { type: "done", payload: { answer } },
    ];
    const body = frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join("");
    await route.fulfill({ status: 200, contentType: "text/event-stream", body });
  });

  await page.goto("/chat");

  await page.getByLabel("Message").fill("how is BTC looking on 1h?");
  await page.getByRole("button", { name: "Send" }).click();

  // .first(): the activity chip can transiently render more than once, which
  // trips Playwright strict mode on a bare locator. We only need one visible.
  await expect(page.locator(".tool-activity-chip").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/RSI 58\.2/)).toBeVisible({ timeout: 10_000 });
  // The recommendation bubble carries its own disclaimer (distinct from the
  // app-shell footer, which also shows it on every page).
  await expect(page.locator(".chat-bubble-disclaimer")).toContainText(DISCLAIMER);
});
