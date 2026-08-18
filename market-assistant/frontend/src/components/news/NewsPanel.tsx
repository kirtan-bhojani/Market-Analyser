export interface NewsItemVM {
  id: number;
  source: string | null;
  title: string | null;
  url: string | null;
  published_at: string | null;
  sentiment: number | null;
  tickers: string[];
}

type Tone = "pos" | "neg" | "neu";

function tone(sentiment: number | null): Tone {
  if (sentiment === null) return "neu";
  if (sentiment > 0.15) return "pos";
  if (sentiment < -0.15) return "neg";
  return "neu";
}

const TONE_LABEL: Record<Tone, string> = {
  pos: "bullish",
  neg: "bearish",
  neu: "neutral",
};

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

/** Sentiment-coded headline list — reuses the desk `.news-row` treatment. */
export function NewsPanel({ items }: { items: NewsItemVM[] }) {
  if (items.length === 0) {
    return <p className="news-empty">No recent news.</p>;
  }
  return (
    <ul className="news-panel">
      {items.map((n) => {
        const t = tone(n.sentiment);
        return (
          <li key={n.id} className={`news-row sentiment-${t}`}>
            <span className={`sent ${t}`} aria-hidden="true" />
            <div>
              <a className="hl" href={n.url ?? "#"} target="_blank" rel="noreferrer">
                {n.title}
              </a>
              <div className="meta">
                {n.source} · {relativeTime(n.published_at)} ·{" "}
                <span className={t === "pos" ? "up" : t === "neg" ? "down" : undefined}>
                  {t === "pos" ? "+ " : t === "neg" ? "− " : ""}
                  {TONE_LABEL[t]}
                </span>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
