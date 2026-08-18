import { useLivePrice } from "../../hooks/useLivePrice";

// Live crypto ticks (the /ws/candles feed is crypto-real-time). Kept short so
// the tape stays glanceable; every value is real — no fabricated prices.
const TAPE_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

function TapeItem({ symbol }: { symbol: string }) {
  const { last, changePct } = useLivePrice(symbol);
  const dir = changePct === null ? "" : changePct >= 0 ? "up" : "down";
  return (
    <div className="tape-item">
      <span className="sym">{symbol.replace("/USDT", "")}</span>
      <span className="px num">{last === null ? "—" : last.toFixed(2)}</span>
      <span className={`chg num ${dir}`}>
        {changePct === null
          ? ""
          : `${changePct >= 0 ? "+" : ""}${(changePct * 100).toFixed(2)}%`}
      </span>
    </div>
  );
}

/** Live price tape across the top of the shell (replaces the old static tape). */
export function PriceTape() {
  return (
    <div className="tape">
      {TAPE_SYMBOLS.map((symbol) => (
        <TapeItem key={symbol} symbol={symbol} />
      ))}
    </div>
  );
}
