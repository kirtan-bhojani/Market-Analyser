export interface TimeframeSwitcherProps {
  value: string;
  onChange: (tf: string) => void;
  options: string[];
}

/** Segmented tab control for the active timeframe. */
export function TimeframeSwitcher({ value, onChange, options }: TimeframeSwitcherProps) {
  return (
    <div role="tablist" aria-label="Timeframe" className="tf-switch" data-testid="tf-switcher">
      {options.map((tf) => (
        <button
          key={tf}
          type="button"
          role="tab"
          aria-selected={tf === value}
          className={`tf-tab${tf === value ? " active" : ""}`}
          onClick={() => onChange(tf)}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
