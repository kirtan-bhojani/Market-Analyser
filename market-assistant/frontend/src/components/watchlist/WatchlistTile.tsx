import { heatColor } from "../../lib/heatColor";
import type { WatchlistTileData } from "../../stores/watchlistStore";
import { DelayBadge } from "../common/DelayBadge";

interface WatchlistTileProps extends WatchlistTileData {
  delayed?: boolean;
  delayMinutes?: number;
}

/** Presentational live-price tile; background heat-mapped by daily % change. */
export function WatchlistTile({ symbol, last, changePct, delayed, delayMinutes }: WatchlistTileProps) {
  const up = changePct >= 0;
  return (
    <div
      className="wl-tile"
      data-testid={`tile-${symbol}`}
      style={{ background: heatColor(changePct) }}
    >
      <div className="wl-tile-top">
        <span className="wl-sym">{symbol}</span>
        <DelayBadge delayed={delayed ?? false} delayMinutes={delayMinutes ?? 0} />
        <span className={`wl-arrow ${up ? "up" : "down"}`} aria-hidden="true">
          {up ? "▲" : "▼"}
        </span>
      </div>
      <div className="wl-price num" data-testid={`tile-${symbol}-price`}>
        {last.toFixed(2)}
      </div>
      <div className="wl-change num" data-testid={`tile-${symbol}-change`}>
        {(changePct * 100).toFixed(2)}%
      </div>
    </div>
  );
}
