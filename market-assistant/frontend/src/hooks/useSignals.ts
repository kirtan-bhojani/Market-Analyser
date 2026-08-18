import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { authedFetch, buildWsUrl } from "../lib/api";
import { parseSignalFrame } from "../lib/wsFrames";
import { useAccessToken } from "./useAccessToken";
import { useWebSocket } from "./useWebSocket";

/** Wire shape of one signal — mirrors the backend `SignalOut` schema. */
export interface SignalOut {
  id: number;
  instrument_id: number | null;
  strategy: string;
  direction: string; // "long" | "short"
  ts: string; // ISO timestamp
  confidence: number | null;
  ref_entry: number | null;
  ref_sl: number | null;
  ref_tp: number | null;
  backtest_ref: string | null;
  meta: Record<string, unknown> | null;
}

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
// Bound the live buffer so a long-lived open feed can't grow without limit.
const MAX_LIVE = 200;

async function fetchSignals(instrumentId: number, strategy?: string): Promise<SignalOut[]> {
  const params = new URLSearchParams({ instrument_id: String(instrumentId) });
  if (strategy) params.set("strategy", strategy);
  const res = await authedFetch(`${API_BASE}/api/signals?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load signals (${res.status})`);
  return res.json();
}

/**
 * Loads REST signal history for `instrumentId`, then layers the live
 * `/ws/signals` stream (channel `signals:{symbol}:{tf}`) on top — deduping by
 * signal id, newest first. Returns the merged `SignalOut[]`.
 */
export function useSignals(
  symbol: string,
  tf: string,
  instrumentId: number,
  strategy?: string,
): SignalOut[] {
  // `tf` is NOT part of the REST query — fetchSignals ignores it — so keeping it
  // in the key would refetch the same history on every timeframe switch.
  const { data: history = [] } = useQuery({
    queryKey: ["signals", instrumentId, strategy ?? null],
    queryFn: () => fetchSignals(instrumentId, strategy),
  });

  const [live, setLive] = useState<SignalOut[]>([]);
  const token = useAccessToken();

  // A new scope — or a different user (token change) — means the buffered live
  // signals belong to another feed; drop them so nothing bleeds across.
  useEffect(() => {
    setLive([]);
  }, [symbol, tf, instrumentId, token]);

  const onMessage = useMemo(
    () => (data: string) => {
      const incoming = parseSignalFrame(data);
      if (!incoming) return; // drop malformed / off-schema frames silently
      setLive((prev) =>
        prev.some((s) => s.id === incoming.id)
          ? prev
          : [incoming, ...prev].slice(0, MAX_LIVE),
      );
    },
    [],
  );

  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/signals`, token) : "";
  // reconnectKey rebuilds the socket on a symbol/tf change (fresh server
  // subscription) instead of leaking the previous feed's signals.
  const { send, status } = useWebSocket(wsUrl, {
    onMessage,
    reconnectKey: `signals:${symbol}:${tf}`,
  });

  useEffect(() => {
    if (status === "open") {
      send({ subscribe: `signals:${symbol}:${tf}` });
    }
  }, [status, symbol, tf, send]);

  return useMemo(() => {
    const seen = new Set<number>();
    const merged: SignalOut[] = [];
    for (const s of [...live, ...history]) {
      if (!seen.has(s.id)) {
        seen.add(s.id);
        merged.push(s);
      }
    }
    return merged;
  }, [live, history]);
}
