import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { HitsFeed } from "../../src/components/scanner/HitsFeed";
import type { ScanHit } from "../../src/lib/scannerTypes";

describe("HitsFeed", () => {
  it("renders each hit with rule name, instrument, and a sparkline", () => {
    const hits: ScanHit[] = [
      {
        rule_id: 1,
        rule_name: "RSI dip",
        instrument_id: 2,
        tf: "5m",
        ts: "2026-01-01T00:05:00Z",
        payload: { rsi: 28.4, rel_volume: 2.3 },
      },
    ];
    render(<HitsFeed hits={hits} />);
    expect(screen.getByText("RSI dip")).toBeInTheDocument();
    expect(screen.getByText(/rsi: 28.4/i)).toBeInTheDocument();
    expect(screen.getByTestId("sparkline-1-2")).toBeInTheDocument();
  });

  it("shows an empty state with no hits yet", () => {
    render(<HitsFeed hits={[]} />);
    expect(screen.getByText(/no hits yet/i)).toBeInTheDocument();
  });

  it("does not crash when a hit has a null/missing payload", () => {
    const hits = [
      {
        rule_id: 3,
        rule_name: "Broken",
        instrument_id: 4,
        tf: "5m",
        ts: "2026-01-01T00:05:00Z",
        payload: null,
      } as unknown as ScanHit,
    ];
    render(<HitsFeed hits={hits} />);
    expect(screen.getByText("Broken")).toBeInTheDocument();
  });
});
