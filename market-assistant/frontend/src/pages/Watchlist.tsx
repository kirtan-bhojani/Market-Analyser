import { WatchlistTileContainer } from "../components/watchlist/WatchlistTileContainer";

const WATCHED_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

export function WatchlistPage() {
  return (
    <div className="watchlist-page" data-testid="watchlist-page">
      <h1 className="page-title">Watchlist</h1>
      <p className="page-sub">Live prices · heat-mapped by session change · crypto real-time</p>

      <div className="wl-grid">
        {WATCHED_SYMBOLS.map((symbol) => (
          <WatchlistTileContainer key={symbol} symbol={symbol} />
        ))}
      </div>

      <p className="disc chart-disc">
        Educational analysis — live prices for study, not trade recommendations.
      </p>
    </div>
  );
}
