import { EmptyState } from "../common/EmptyState";
import type { ScanHit } from "../../lib/scannerTypes";
import { Sparkline } from "./Sparkline";

interface HitsFeedProps {
  hits: ScanHit[];
}

/**
 * Live feed of scanner hits. Each hit shows its rule name, the instrument /
 * timeframe, the matched indicator payload (rendered as `key: value` pairs),
 * and a tiny sparkline of the payload values.
 */
export function HitsFeed({ hits }: HitsFeedProps) {
  if (hits.length === 0) {
    return (
      <EmptyState
        glyph="◔"
        title="No hits yet"
        message="Once rules are enabled, matching symbols stream into this feed in real time as candles close."
      />
    );
  }

  return (
    <ul className="hits-feed" data-testid="hits-feed">
      {hits.map((hit, i) => {
        // Prod payloads use period-suffixed keys (e.g. `rsi:14`); strip the
        // suffix so we can read bare indicator names and show clean labels.
        const bare: Record<string, number | null> = Object.fromEntries(
          Object.entries(hit.payload ?? {}).map(([k, v]) => [k.split(":")[0], v]),
        );
        return (
          <li className="hit-item" key={`${hit.rule_id}-${hit.instrument_id}-${hit.ts}-${i}`}>
            <div className="hit-head">
              <span className="hit-name">{hit.rule_name}</span>
              <span className="hit-meta num">
                #{hit.instrument_id} · {hit.tf}
              </span>
            </div>
            <div className="hit-body">
              <span className="hit-payload num">
                {Object.entries(bare)
                  .filter(([, v]) => v !== null)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(", ")}
              </span>
              <span
                className="hit-spark"
                data-testid={`sparkline-${hit.rule_id}-${hit.instrument_id}`}
              >
                <Sparkline points={[bare.rsi ?? 0, bare.rel_volume ?? 0]} />
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
