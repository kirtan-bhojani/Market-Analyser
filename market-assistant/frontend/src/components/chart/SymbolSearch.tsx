const KNOWN_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

export interface SymbolSearchProps {
  value: string;
  onChange: (symbol: string) => void;
}

/** Symbol input with datalist suggestions; upper-cases as you type. */
export function SymbolSearch({ value, onChange }: SymbolSearchProps) {
  return (
    <div className="sym-search">
      <span className="sym-search-ic" aria-hidden="true">
        ⌕
      </span>
      <input
        list="symbol-options"
        data-testid="symbol-search"
        aria-label="Chart symbol"
        placeholder="Symbol — BTC/USDT"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
      />
      <datalist id="symbol-options">
        {KNOWN_SYMBOLS.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </div>
  );
}
