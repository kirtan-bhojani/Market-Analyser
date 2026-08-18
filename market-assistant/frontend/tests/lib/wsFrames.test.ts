import { describe, expect, it } from "vitest";

import { parseCandleFrame, parseScanHitFrame, parseSignalFrame } from "../../src/lib/wsFrames";

describe("parseCandleFrame", () => {
  it("returns the candle for a well-formed frame", () => {
    const c = parseCandleFrame(
      JSON.stringify({ ts: "2024-06-15T14:00:00Z", o: 1, h: 2, l: 0.5, c: 1.5, v: 10 }),
    );
    expect(c).not.toBeNull();
    expect(c?.c).toBe(1.5);
  });

  it("returns null for invalid JSON", () => {
    expect(parseCandleFrame("{not json")).toBeNull();
  });

  it("returns null when a numeric field is missing (e.g. a signal frame)", () => {
    expect(parseCandleFrame(JSON.stringify({ id: 1, strategy: "orb", ts: "x" }))).toBeNull();
  });

  it("returns null when ts is absent", () => {
    expect(parseCandleFrame(JSON.stringify({ o: 1, h: 2, l: 0.5, c: 1.5, v: 10 }))).toBeNull();
  });

  it("returns null when a field is NaN/Infinity", () => {
    expect(
      parseCandleFrame(JSON.stringify({ ts: "x", o: 1, h: 2, l: 0.5, c: null, v: 10 })),
    ).toBeNull();
  });

  it("returns null for a non-object frame (array/number)", () => {
    expect(parseCandleFrame("[1,2,3]")).toBeNull();
    expect(parseCandleFrame("42")).toBeNull();
  });
});

describe("parseSignalFrame", () => {
  it("returns the signal for a frame with a numeric id", () => {
    const s = parseSignalFrame(JSON.stringify({ id: 7, strategy: "orb", direction: "long" }));
    expect(s?.id).toBe(7);
  });

  it("returns null for invalid JSON", () => {
    expect(parseSignalFrame("nope")).toBeNull();
  });

  it("returns null when id is missing", () => {
    expect(parseSignalFrame(JSON.stringify({ strategy: "orb" }))).toBeNull();
  });
});

describe("parseScanHitFrame", () => {
  const base = {
    rule_id: 1,
    rule_name: "RSI dip",
    instrument_id: 2,
    tf: "5m",
    ts: "2026-01-01T00:05:00Z",
    payload: { rsi: 28.4 },
  };

  it("returns the hit for a well-formed frame", () => {
    const h = parseScanHitFrame(JSON.stringify(base));
    expect(h).not.toBeNull();
    expect(h?.rule_id).toBe(1);
    expect(h?.payload.rsi).toBe(28.4);
  });

  it("normalizes a missing/null payload to {}", () => {
    const h = parseScanHitFrame(JSON.stringify({ ...base, payload: null }));
    expect(h).not.toBeNull();
    expect(h?.payload).toEqual({});
    const h2 = parseScanHitFrame(
      JSON.stringify({ rule_id: 1, rule_name: "x", instrument_id: 2, tf: "5m", ts: "t" }),
    );
    expect(h2?.payload).toEqual({});
  });

  it("returns null for invalid JSON or missing id fields", () => {
    expect(parseScanHitFrame("{bad")).toBeNull();
    expect(parseScanHitFrame(JSON.stringify({ ...base, rule_id: "1" }))).toBeNull();
    expect(parseScanHitFrame(JSON.stringify({ ...base, ts: "" }))).toBeNull();
    expect(parseScanHitFrame("[1,2]")).toBeNull();
  });
});
