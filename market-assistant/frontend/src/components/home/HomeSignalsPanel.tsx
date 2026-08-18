import { useQueries, useQuery } from "@tanstack/react-query";

import { getInstruments, getSignals, type SignalDto } from "../../lib/api";
import type { SignalOut } from "../../hooks/useSignals";
import { EmptyState } from "../common/EmptyState";
import { SignalFeedCard } from "../strategies/SignalFeedCard";

// The dashboard focuses on the live crypto majors; signals for these
// instruments are fetched for real (no fabricated setups).
const HOME_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];
const MAX_CARDS = 4;

/** Active-signals panel wired to the real /api/signals feed for the home
 * instruments. Shows loading / error / empty states honestly — never a
 * fabricated setup. */
export function HomeSignalsPanel() {
  const instrumentsQuery = useQuery({
    queryKey: ["home-instruments"],
    queryFn: () => getInstruments(),
  });

  const picks = (instrumentsQuery.data ?? []).filter((i) =>
    HOME_SYMBOLS.includes(i.symbol),
  );

  const signalQueries = useQueries({
    queries: picks.map((instrument) => ({
      queryKey: ["home-signals", instrument.id],
      queryFn: () => getSignals(instrument.id),
    })),
  });

  if (instrumentsQuery.isLoading) {
    return <p className="page-sub">Loading signals…</p>;
  }
  if (instrumentsQuery.isError) {
    return (
      <EmptyState
        glyph="!"
        title="Couldn’t load signals"
        message="The signals service is unavailable right now. It will populate once reachable."
      />
    );
  }

  const signals: SignalDto[] = signalQueries
    .flatMap((q) => q.data ?? [])
    .sort((a, b) => b.ts.localeCompare(a.ts))
    .slice(0, MAX_CARDS);

  if (signals.length === 0) {
    return (
      <EmptyState
        glyph="◔"
        title="No active signals"
        message="Enabled strategies stream detected setups here as candles close."
      />
    );
  }

  return (
    <>
      {signals.map((s) => (
        <SignalFeedCard key={s.id} signal={s as SignalOut} backtestStats={null} />
      ))}
    </>
  );
}
