import { describe, expect, it } from "vitest";

import { backtestRefetchInterval, MAX_POLL_FAILURES } from "../../src/hooks/useBacktest";

describe("backtestRefetchInterval (T3-19)", () => {
  it("polls every 2s while running with no failures", () => {
    expect(backtestRefetchInterval("running", 0)).toBe(2000);
    expect(backtestRefetchInterval(undefined, 0)).toBe(2000);
  });

  it("stops on a terminal status", () => {
    expect(backtestRefetchInterval("done", 0)).toBe(false);
    expect(backtestRefetchInterval("failed", 0)).toBe(false);
  });

  it("stops polling once the endpoint has failed repeatedly", () => {
    expect(backtestRefetchInterval("running", MAX_POLL_FAILURES - 1)).toBe(2000);
    expect(backtestRefetchInterval("running", MAX_POLL_FAILURES)).toBe(false);
    expect(backtestRefetchInterval("running", MAX_POLL_FAILURES + 5)).toBe(false);
  });
});
