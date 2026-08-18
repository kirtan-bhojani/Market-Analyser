import { useCallback, useEffect, useRef, useState } from "react";

export type WebSocketStatus = "connecting" | "open" | "closed";

export interface UseWebSocketOptions {
  onMessage: (data: string) => void;
  reconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
  /**
   * Opaque identity for the subscription (e.g. `candles:BTC/USDT:1m`). When it
   * changes the socket is torn down and reopened, so a symbol/tf switch drops
   * the previous server subscription and starts fresh — no stale-channel leak.
   * Kept off the URL because browsers reject fragments in WebSocket URLs.
   */
  reconnectKey?: string;
}

/**
 * Reconnecting WebSocket hook. Exposes a live `status` and a `send()` that
 * JSON-encodes its argument. Auto-reconnects with EXPONENTIAL backoff
 * (base → 2×base → 4×base … capped at `maxReconnectDelayMs`), resetting to the
 * base delay after any successful open. Each reconnect reads the LATEST `url`
 * (via a ref) so a token refresh that lands mid-backoff reconnects with the
 * fresh `?token=` rather than replaying the stale one. No-ops gracefully where
 * `WebSocket` is unavailable (e.g. server-side / jsdom without a stub).
 */
export function useWebSocket(
  url: string,
  {
    onMessage,
    reconnectDelayMs = 1000,
    maxReconnectDelayMs = 30000,
    reconnectKey,
  }: UseWebSocketOptions,
) {
  const [status, setStatus] = useState<WebSocketStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  // Always reconnect against the freshest url (freshest token), even if it
  // changed while a socket was mid-backoff.
  const urlRef = useRef(url);
  urlRef.current = url;

  useEffect(() => {
    if (typeof WebSocket === "undefined") {
      setStatus("closed");
      return;
    }
    // Callers pass "" when the auth token isn't available yet (e.g. signed
    // out) — stay closed rather than opening a socket with no `?token=`.
    if (!url) {
      setStatus("closed");
      return;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let attempt = 0;

    function connect() {
      const ws = new WebSocket(urlRef.current);
      wsRef.current = ws;
      setStatus("connecting");

      ws.onopen = () => {
        attempt = 0; // reset backoff once a connection actually succeeds
        setStatus("open");
      };
      ws.onmessage = (event: MessageEvent<string>) => onMessageRef.current(event.data);
      ws.onclose = () => {
        setStatus("closed");
        if (!cancelled) {
          const delay = Math.min(reconnectDelayMs * 2 ** attempt, maxReconnectDelayMs);
          attempt += 1;
          reconnectTimer = setTimeout(connect, delay);
        }
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      const ws = wsRef.current;
      if (ws) {
        // Detach handlers BEFORE close: a closing socket still fires onclose
        // (and can fire onmessage for buffered frames), which would flip status
        // or deliver a stale message into the next effect's context.
        ws.onopen = null;
        ws.onmessage = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
      }
    };
  }, [url, reconnectDelayMs, maxReconnectDelayMs, reconnectKey]);

  const send = useCallback((data: unknown) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return { status, send };
}
