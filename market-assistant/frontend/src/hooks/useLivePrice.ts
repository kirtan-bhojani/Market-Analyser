import { useEffect, useRef, useState } from "react";

import { authedFetch, buildWsUrl } from "../lib/api";
import { parseCandleFrame } from "../lib/wsFrames";
import type { Candle } from "./useCandles";
import { useAccessToken } from "./useAccessToken";
import { useWebSocket } from "./useWebSocket";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface LivePrice {
  last: number | null;
  changePct: number | null;
}

/**
 * Live last-price + daily % change for one symbol over `/ws/candles`.
 *
 * The day% baseline is the TRUE UTC day open, seeded from REST (the 1d candle)
 * so a mid-day subscription doesn't measure change from an arbitrary intraday
 * point; the live 1m stream updates `last` and reseeds on day rollover.
 */
export function useLivePrice(symbol: string): LivePrice {
  const [last, setLast] = useState<number | null>(null);
  const [dayOpen, setDayOpen] = useState<number | null>(null);
  const lastDayRef = useRef<string | null>(null);

  useEffect(() => {
    setLast(null);
    setDayOpen(null);
    lastDayRef.current = null;
    let cancelled = false;
    const now = new Date();
    const dayStart = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
    );
    const params = new URLSearchParams({
      symbol,
      tf: "1d",
      from: dayStart.toISOString(),
      to: now.toISOString(),
    });
    authedFetch(`${API_BASE}/candles?${params.toString()}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { candles?: Candle[] } | null) => {
        if (cancelled || !body?.candles?.length) return;
        const dayCandle = body.candles[0];
        setDayOpen(dayCandle.o);
        lastDayRef.current = dayCandle.ts.slice(0, 10);
      })
      .catch(() => {
        /* offline — fall back to the first live candle's open */
      });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const onMessage = (data: string) => {
    // Only trust well-formed candle frames: a non-candle frame (or a malformed
    // one) would otherwise set `last` to undefined and crash consumers doing
    // `last.toFixed(...)`. Shared validator, same guard as useCandles/useSignals.
    const candle = parseCandleFrame(data);
    if (!candle) return;
    const day = candle.ts.slice(0, 10);
    if (lastDayRef.current !== day) {
      lastDayRef.current = day;
      setDayOpen(candle.o);
    }
    setLast(candle.c);
  };

  const token = useAccessToken();
  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/candles`, token) : "";
  // reconnectKey rebuilds the socket on a symbol change, dropping the previous
  // symbol's subscription.
  const { status, send } = useWebSocket(wsUrl, {
    onMessage,
    reconnectKey: `candles:${symbol}:1m`,
  });

  useEffect(() => {
    if (status === "open") send({ subscribe: `candles:${symbol}:1m` });
  }, [status, symbol, send]);

  const changePct =
    last !== null && dayOpen !== null && dayOpen !== 0 ? (last - dayOpen) / dayOpen : null;
  return { last, changePct };
}
