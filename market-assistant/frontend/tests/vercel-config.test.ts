// Phase 12.5 Task 1: vercel.json is well-formed for a Vite SPA on Vercel.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const config = JSON.parse(
  readFileSync(resolve(process.cwd(), "vercel.json"), "utf-8"),
);

describe("vercel.json", () => {
  it("outputs the Vite dist directory", () => {
    expect(config.outputDirectory).toBe("dist");
  });

  it("disables Vercel's own git auto-deploy (deploys go through CI only)", () => {
    expect(config.git.deploymentEnabled).toBe(false);
  });

  it("has an SPA fallback rewrite so deep links resolve to index.html", () => {
    expect(config.rewrites).toContainEqual({
      source: "/(.*)",
      destination: "/index.html",
    });
  });

  it("sets immutable cache headers on hashed assets", () => {
    const assetRule = config.headers.find(
      (h: { source: string }) => h.source === "/assets/(.*)",
    );
    const cacheControl = assetRule.headers.find(
      (x: { key: string }) => x.key === "Cache-Control",
    );
    expect(cacheControl.value).toBe("public, max-age=31536000, immutable");
  });
});
