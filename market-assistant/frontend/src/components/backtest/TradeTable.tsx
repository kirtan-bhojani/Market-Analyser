import type { EquityPoint } from "../../hooks/useBacktest";

/**
 * Tabular view of the equity curve points (timestamp + equity value).
 */
export function TradeTable({ equityCurve }: { equityCurve: EquityPoint[] }) {
  return (
    <table className="trade-table" data-testid="trade-table">
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Equity</th>
        </tr>
      </thead>
      <tbody>
        {equityCurve.map((p) => (
          <tr key={p.ts}>
            <td>{p.ts}</td>
            <td className="num">{p.value.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
