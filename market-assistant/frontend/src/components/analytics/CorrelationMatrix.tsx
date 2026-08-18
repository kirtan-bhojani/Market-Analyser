export interface CorrelationVM {
  symbols: string[];
  // null = a pair with no overlapping history (correlation undefined).
  matrix: (number | null)[][];
}

/** Diverging fill over the panel surface: red (−1) ↔ transparent (0) ↔ green (+1).
 * Magnitude sets alpha so 0 reads as the neutral surface; the printed value is
 * the secondary (non-color) encoding, so it stays legible under CVD. A null
 * (no-data) cell stays the neutral surface. */
function cellColor(v: number | null): string {
  if (v === null) return "transparent";
  const t = Math.max(-1, Math.min(1, v));
  const alpha = 0.12 + 0.55 * Math.abs(t);
  return t >= 0 ? `rgba(18, 133, 90, ${alpha})` : `rgba(200, 50, 75, ${alpha})`;
}

export function CorrelationMatrix({ data }: { data: CorrelationVM }) {
  return (
    <div className="matrix-scroll">
      <table className="correlation-matrix" data-testid="correlation-matrix">
        <thead>
          <tr>
            <th aria-label="symbol" />
            {data.symbols.map((s) => (
              <th key={s}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.symbols.map((rowSym, r) => (
            <tr key={rowSym}>
              <th scope="row">{rowSym}</th>
              {data.symbols.map((colSym, c) => {
                // Guard ragged/short rows: a missing cell reads as no-data.
                const v = data.matrix[r]?.[c] ?? null;
                const text = v === null ? "—" : v.toFixed(2);
                return (
                  <td
                    key={colSym}
                    className="num"
                    style={{ background: cellColor(v) }}
                    title={`${rowSym} · ${colSym}: ${text}`}
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
