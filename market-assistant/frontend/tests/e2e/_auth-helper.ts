import type { Page } from "@playwright/test";

const USER = { id: "00000000-0000-0000-0000-000000000001", email: "demo@example.com" };

/**
 * Seed a persisted, authenticated session so RequireAuth passes on load.
 *
 * Two localStorage keys must be seeded, because two things gate auth:
 *
 * 1. `market-assistant-auth` — the zustand authStore persists `{user}` here.
 *    `onRehydrateStorage` sets `isAuthenticated = user != null`, so this alone
 *    makes the guard pass on FIRST paint (no login flash).
 *
 * 2. `sb-127-auth-token` — supabase-js's own session store. `initAuth()`
 *    (main.tsx) subscribes to `onAuthStateChange`, which fires `INITIAL_SESSION`
 *    on load and calls `setSession(recoveredSession)`. Without a stored session
 *    that resolves to null and clobbers step 1 back to unauthenticated. Seeding
 *    a non-expired session here keeps the store authenticated after recovery.
 *    The key is `sb-${hostname.split(".")[0]}-auth-token`; with the dummy build
 *    URL `http://127.0.0.1:54321` the ref is `127`. auth-js only requires
 *    `access_token`/`refresh_token`/`expires_at` to accept the session (no JWT
 *    signature check), and a far-future `expires_at` avoids a network refresh.
 *
 * Must run BEFORE the first `page.goto(...)`. NOT a `*.spec.ts` file, so
 * Playwright's testMatch does not collect it as a test. The fixed email keeps
 * the AppShell rail-foot deterministic for the design-smoke screenshots.
 */
export async function presetAuth(page: Page) {
  await page.addInitScript(
    ([user]) => {
      window.localStorage.setItem(
        "market-assistant-auth",
        JSON.stringify({ state: { user }, version: 0 }),
      );
      window.localStorage.setItem(
        "sb-127-auth-token",
        JSON.stringify({
          // Raw user UUID: the backend's non-prod auth accepts this as both a
          // Bearer (get_current_user_id) and a WS ?token= (authenticate_ws),
          // scoping API data to this user. A non-UUID string 401s/403s.
          access_token: user.id,
          refresh_token: "test-refresh-token",
          token_type: "bearer",
          // Far future (year ~2286) so auth-js treats the session as unexpired
          // and never attempts a (network) refresh against the dummy backend.
          expires_at: 9999999999,
          expires_in: 3600,
          user,
        }),
      );
    },
    [USER],
  );
}
