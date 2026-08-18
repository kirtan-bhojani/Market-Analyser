import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    // Supabase client (src/lib/supabase.ts) throws at import if these are
    // unset. CI has no .env, so supply dummy values here — tests that need a
    // real client `vi.mock` the module; the rest just need import not to throw.
    env: {
      VITE_SUPABASE_URL: "http://127.0.0.1:54321",
      VITE_SUPABASE_ANON_KEY: "test-anon-key",
    },
    // Unit tests are *.test.*; Playwright e2e specs (*.spec.ts) run separately.
    include: ["tests/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**", "node_modules/**"],
  },
});
