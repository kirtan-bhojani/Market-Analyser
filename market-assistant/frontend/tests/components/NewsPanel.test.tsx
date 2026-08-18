import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NewsPanel, type NewsItemVM } from "../../src/components/news/NewsPanel";

const items: NewsItemVM[] = [
  {
    id: 1,
    source: "CoinDesk",
    title: "BTC rallies",
    url: "https://x/1",
    published_at: "2026-07-10T00:00:00Z",
    sentiment: 0.8,
    tickers: ["BTC/USDT"],
  },
  {
    id: 2,
    source: "Reuters",
    title: "Rates worry markets",
    url: "https://x/2",
    published_at: "2026-07-09T22:00:00Z",
    sentiment: -0.6,
    tickers: ["NIFTY"],
  },
];

describe("NewsPanel", () => {
  it("renders each headline as a link with a sentiment-coded row", () => {
    render(<NewsPanel items={items} />);
    const pos = screen.getByRole("link", { name: /BTC rallies/i });
    const neg = screen.getByRole("link", { name: /Rates worry markets/i });
    expect(pos).toHaveAttribute("href", "https://x/1");
    expect(pos.closest("li")).toHaveClass("sentiment-pos");
    expect(neg.closest("li")).toHaveClass("sentiment-neg");
  });

  it("renders an empty-state message when there is no news", () => {
    render(<NewsPanel items={[]} />);
    expect(screen.getByText(/no recent news/i)).toBeInTheDocument();
  });
});
