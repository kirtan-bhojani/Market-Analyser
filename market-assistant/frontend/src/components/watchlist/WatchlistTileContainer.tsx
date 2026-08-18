import { useLivePrice } from "../../hooks/useLivePrice";
import { WatchlistTile } from "./WatchlistTile";

/** Owns a live-price subscription for one symbol and derives daily % change. */
export function WatchlistTileContainer({ symbol }: { symbol: string }) {
  const { last, changePct } = useLivePrice(symbol);

  if (last === null || changePct === null) {
    return (
      <div className="wl-tile wl-tile-loading skel" data-testid={`tile-${symbol}-loading`}>
        <div className="wl-tile-top">
          <span className="wl-sym">{symbol}</span>
        </div>
        <div className="bar w60" />
        <div className="bar w40" />
      </div>
    );
  }

  return <WatchlistTile symbol={symbol} last={last} changePct={changePct} />;
}
