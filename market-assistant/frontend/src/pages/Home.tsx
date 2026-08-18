import { useEffect, useRef, useState } from "react";

import { EmptyState } from "../components/common/EmptyState";
import { Panel } from "../components/common/Panel";
import { EmbeddedMiniChat } from "../components/home/EmbeddedMiniChat";
import { HomeSignalsPanel } from "../components/home/HomeSignalsPanel";
import { NewsPanel } from "../components/news/NewsPanel";
import { HitsFeed } from "../components/scanner/HitsFeed";
import { WatchlistTileContainer } from "../components/watchlist/WatchlistTileContainer";
import { createSession } from "../lib/api";
import { useNews } from "../hooks/useNews";
import { useScanHits } from "../hooks/useScanHits";

const WATCH_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

export function Home() {
  const { data: news } = useNews();
  const hits = useScanHits();

  // Real persisted chat session (backend types session_id as uuid.UUID and
  // 404s unknown sessions); created once, guarded against StrictMode.
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const createdRef = useRef(false);
  useEffect(() => {
    if (createdRef.current) return;
    createdRef.current = true;
    let cancelled = false;
    createSession()
      .then((s) => {
        if (!cancelled) setChatSessionId(s.id);
      })
      .catch(() => {
        /* leave chat disabled if session creation fails */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div data-testid="home-dashboard">
      <h1 className="page-title">Home</h1>
      <p className="page-sub">Live crypto · delayed equities · educational analysis only</p>

      {/* Market breadth & regime have no live backend source yet — show an
          honest placeholder rather than fabricated gauges. */}
      <Panel title="Market Breadth & Regime">
        <EmptyState
          glyph="▤"
          title="Breadth & regime unavailable"
          message="A live market-breadth / regime feed isn’t wired yet. This panel stays empty rather than showing placeholder numbers."
        />
      </Panel>

      <div className="grid-2">
        <div className="col">
          <Panel title="Active Signals" tag="analysis only">
            <HomeSignalsPanel />
          </Panel>

          <Panel title="Top Scanner Hits" tag="live">
            <HitsFeed hits={hits} />
          </Panel>
        </div>

        <div className="col">
          <Panel title="News & Sentiment">
            <NewsPanel items={news ?? []} />
          </Panel>

          <Panel title="Watchlist" tag="live">
            <div className="watch">
              {WATCH_SYMBOLS.map((symbol) => (
                <WatchlistTileContainer key={symbol} symbol={symbol} />
              ))}
            </div>
          </Panel>

          <Panel title="Ask the desk" tag="beta">
            {chatSessionId ? (
              <EmbeddedMiniChat sessionId={chatSessionId} />
            ) : (
              <p className="page-sub">Starting a session…</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
