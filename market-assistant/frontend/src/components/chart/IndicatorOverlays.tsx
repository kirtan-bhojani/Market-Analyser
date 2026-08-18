export interface OverlayToggles {
  ema: boolean;
  vwap: boolean;
  bollinger: boolean;
}

export interface IndicatorOverlaysProps {
  value: OverlayToggles;
  onChange: (next: OverlayToggles) => void;
}

const ITEMS: Array<{ key: keyof OverlayToggles; label: string; swatch: string }> = [
  { key: "ema", label: "EMA(21)", swatch: "var(--chart-ema)" },
  { key: "vwap", label: "VWAP", swatch: "var(--chart-vwap)" },
  { key: "bollinger", label: "Bollinger", swatch: "var(--chart-bb)" },
];

/** Overlay toggles shown as swatched pills; each is a real checkbox for a11y. */
export function IndicatorOverlays({ value, onChange }: IndicatorOverlaysProps) {
  const toggle = (key: keyof OverlayToggles) => onChange({ ...value, [key]: !value[key] });
  return (
    <div className="ind-overlays" data-testid="indicator-overlays">
      {ITEMS.map(({ key, label, swatch }) => (
        <label key={key} className={`ind-pill${value[key] ? " on" : ""}`}>
          <input type="checkbox" checked={value[key]} onChange={() => toggle(key)} />
          <span className="ind-swatch" style={{ background: swatch }} aria-hidden="true" />
          {label}
        </label>
      ))}
    </div>
  );
}
